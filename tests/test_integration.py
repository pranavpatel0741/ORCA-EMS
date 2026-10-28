"""M8 integration check (PLAN §15 M8): one surge run's log contains every coordination
mechanism, and no committed action violates a rule.

Runs the agent orchestration with the scripted backend (no network). Hospital A is given a
deliberately short nurse roster so a staff request happens; this fixture is test-only.
"""

import pytest

from orca_agents.llm_cache import LLMClient
from orca_agents.orchestrator import AgentPolicy
from orca_agents.scripted import ScriptedBackend
from sim.engine import Engine
from sim.events import EventType
from sim.generator import generate
from tests.invariants import check_invariants


@pytest.fixture(scope="module")
def surge_log(tmp_path_factory):
    scenario = generate(7, "surge")
    for h in scenario.hospitals:
        if h.id == "A":
            h.nurses_total, h.min_nurse_coverage = 1, 1
    policy = AgentPolicy(client=LLMClient(ScriptedBackend(), mode="live",
                                          cache_dir=tmp_path_factory.mktemp("cache")))
    engine = Engine(scenario, policy, info="partial", tick_hook=check_invariants)
    engine.run()
    return engine


def messages(engine, mtype):
    return [e.payload for e in engine.log.of_type(EventType.MESSAGE) if e.payload["type"] == mtype]


def test_ambulance_conflict_between_two_incidents(surge_log):
    conflicts = [m for m in messages(surge_log, "ESCALATE")
                 if (m.get("proposed_action") or {}).get("type") == "reassign"]
    assert conflicts
    c = conflicts[0]["proposed_action"]
    assert c["from_call"] != c["to_call"]
    assert messages(surge_log, "RESOLVE")


def test_hospital_counter_on_capacity(surge_log):
    assert messages(surge_log, "COUNTER")
    assert messages(surge_log, "PROPOSE")


def test_staff_request_and_response(surge_log):
    assert messages(surge_log, "STAFF_REQUEST") and messages(surge_log, "STAFF_RESPONSE")


def test_mutual_aid_exchange(surge_log):
    assert messages(surge_log, "MUTUAL_AID_REQUEST") and messages(surge_log, "MUTUAL_AID_RESPONSE")
    activated = [m for m in messages(surge_log, "STATUS")
                 if (m.get("proposed_action") or {}).get("units_activated")]
    assert activated


def test_staged_ambulance_released_by_scene_secured(surge_log):
    changes = surge_log.log.of_type(EventType.UNIT_STATE_CHANGED)
    secured = {e.payload["incident_id"]: e.tick for e in surge_log.log.of_type(
        EventType.SCENE_SECURED)}
    released = []
    for e in changes:
        if e.payload.get("to") != "STAGING":
            continue
        unit, inc = e.payload["unit_id"], e.payload.get("incident_id")
        nxt = next((x for x in changes if x.payload.get("unit_id") == unit and x.tick > e.tick
                    or (x.tick == e.tick and x is not e and x.payload.get("unit_id") == unit
                        and x.payload.get("from") == "STAGING")), None)
        if nxt and nxt.payload["from"] == "STAGING" and secured.get(inc) == nxt.tick:
            released.append(unit)
    assert released, "a staged ambulance should move in when police secure the scene"


def test_at_least_one_escalated_decision(surge_log):
    esc = surge_log.log.of_type(EventType.ESCALATED)
    assert esc
    decided = surge_log.log.of_type(EventType.APPROVED) + \
        surge_log.log.of_type(EventType.OVERRIDDEN)
    assert len(decided) >= len(esc) - len(surge_log.pending_approvals)


def test_zero_commits_violate_a_rule(surge_log):
    for c in surge_log.commits:
        if c["committed"]:
            assert all(r["level"] != "block" for r in c["results"])
    validated = surge_log.log.of_type(EventType.PROPOSAL_VALIDATED)
    committed = surge_log.log.of_type(EventType.COMMITTED)
    assert len(committed) <= len(validated)
