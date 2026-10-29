"""Agents, cache, orchestration, confidence, approval. No network: scripted or fake backends."""

from types import SimpleNamespace

import pytest

from baselines.rule_based import RuleBasedPolicy
from orca_agents import allocator, assessment, dispatch, hospital_agent
from orca_agents.confidence import score
from orca_agents.llm_cache import CacheMiss, LLMClient, OpenAIAgentsBackend
from orca_agents.models import (
    AdmissionDecision,
    DispatchPlan,
    PriorityReport,
    Resolution,
    StaffDecision,
)
from orca_agents.orchestrator import AgentPolicy
from orca_agents.scripted import ScriptedBackend
from sim.actions import RouteToHospital
from sim.engine import Engine
from sim.events import EventType
from sim.generator import generate
from tests.invariants import check_invariants


class Recorder(RuleBasedPolicy):
    def __init__(self):
        super().__init__()
        self.obs = []

    def decide(self, obs):
        self.obs.append(obs.model_copy(deep=True))
        return super().decide(obs)


@pytest.fixture(scope="module")
def surge_obs():
    rec = Recorder()
    Engine(generate(7, "surge"), rec, info="partial").run(until=90)
    return rec.obs


def obs_with(observations, predicate):
    return next(o for o in observations if predicate(o))


def client(tmp_path, backend=None, mode="live"):
    return LLMClient(backend if backend is not None else ScriptedBackend(), mode=mode,
                     cache_dir=tmp_path)


def agent_run(name, tmp_path, negotiate=True, info="partial", backend=None, hook=True,
              scenario=None):
    policy = AgentPolicy(negotiate=negotiate, client=client(tmp_path, backend))
    engine = Engine(scenario or generate(7, "surge"), policy, info=info,
                    tick_hook=check_invariants if hook else None)
    engine.run()
    return engine


# --- each agent returns its typed output on a sample input --------------------------------------

def test_each_agent_returns_typed_output(surge_obs, tmp_path):
    c = client(tmp_path)
    obs = obs_with(surge_obs, lambda o: "MCI-2" in o.incidents and o.incidents["MCI-2"]
                   .scene_reported and o.units_needing_destination())
    report, _ = c.call(assessment.SPEC, assessment.payload(obs.incidents["MCI-2"]))
    assert isinstance(report, PriorityReport) and report.mode == "MCI"
    plan, _ = c.call(dispatch.SPEC, dispatch.payload(obs, {"MCI-2": report}, []))
    assert isinstance(plan, DispatchPlan)
    unit = obs.units_needing_destination()[0]
    props = [{"unit_id": unit.id, "eta_min": 5, "patients": []}]
    dec, _ = c.call(hospital_agent.spec(obs, "A"),
                    hospital_agent.admission_payload(obs, "A", props))
    assert isinstance(dec, AdmissionDecision)
    staff, _ = c.call(hospital_agent.spec(obs, "C", staff=True),
                      hospital_agent.staff_payload(obs, "C", "A", 1, "test"))
    assert isinstance(staff, StaffDecision)
    res, _ = c.call(allocator.SPEC, allocator.payload(
        obs, [{"type": "route_unresolved", "unit_id": unit.id, "last_hospital": "A"}], []))
    assert isinstance(res, Resolution)


def test_openai_backend_builds_sdk_agent_with_tools(monkeypatch, surge_obs):
    """The real backend wires instructions, tools and output type into an SDK Agent."""
    import agents

    seen = {}

    async def fake_run(agent, prompt, **kw):
        seen["agent"], seen["prompt"], seen["kw"] = agent, prompt, kw
        out = PriorityReport(incident_id="X", mode="SINGLE",
                             estimated={"critical": 1}, needs_police=False, needs_fire=False,
                             urgency=0.9, rationale="test")
        usage = SimpleNamespace(total_tokens=123)
        return SimpleNamespace(final_output_as=lambda t: out,
                               context_wrapper=SimpleNamespace(usage=usage))

    monkeypatch.setattr(agents.Runner, "run", fake_run)
    backend = OpenAIAgentsBackend(model="test-model")
    out, tokens = backend.run(assessment.SPEC, {"call": {}}, None)
    assert out.urgency == 0.9 and tokens == 123
    agent = seen["agent"]
    assert agent.model == "test-model" and agent.output_type is PriorityReport
    assert {t.name for t in agent.tools} == {"get_incident", "get_scene_reports"}
    assert "Assessment agent" in agent.instructions


# --- cache ---------------------------------------------------------------------------------------

class CountingBackend(ScriptedBackend):
    def __init__(self):
        self.calls = 0

    def run(self, spec, payload, context):
        self.calls += 1
        return super().run(spec, payload, context)


def test_cache_modes(surge_obs, tmp_path):
    inc = obs_with(surge_obs, lambda o: "MCI-2" in o.incidents).incidents["MCI-2"]
    backend = CountingBackend()
    live = client(tmp_path, backend, "live")
    out1, rec1 = live.call(assessment.SPEC, assessment.payload(inc))
    out2, rec2 = live.call(assessment.SPEC, assessment.payload(inc))
    assert backend.calls == 1 and not rec1.cache_hit and rec2.cache_hit and out1 == out2
    client(tmp_path, backend, "record").call(assessment.SPEC, assessment.payload(inc))
    assert backend.calls == 2  # record always calls
    replay = LLMClient(None, mode="cache_only", cache_dir=tmp_path, model_name="scripted")
    out3, rec3 = replay.call(assessment.SPEC, assessment.payload(inc))
    assert rec3.cache_hit and out3 == out1
    with pytest.raises(CacheMiss):
        replay.call(assessment.SPEC, {**assessment.payload(inc), "other": 1})


def test_cache_only_replays_identical_run(tmp_path):
    def comparable(engine):
        rows = []
        for e in engine.log.events:
            p = dict(e.payload)
            if e.type == EventType.LLM_CALL:
                p.pop("latency_ms"), p.pop("cache_hit")
                p["model"] = "-"
            rows.append((e.tick, e.type, e.actor, p))
        return rows

    recorded = agent_run("agents", tmp_path, backend=ScriptedBackend(), hook=False)
    policy = AgentPolicy(client=LLMClient(None, mode="cache_only", cache_dir=tmp_path,
                                          model_name="scripted"))
    replay = Engine(generate(7, "surge"), policy, info="partial")
    replay.run()
    assert comparable(replay) == comparable(recorded)


# --- orchestration -------------------------------------------------------------------------------

class BrokenDispatch(ScriptedBackend):
    def run(self, spec, payload, context):
        if spec.agent_id == "dispatch":
            raise ValueError("malformed output")
        return super().run(spec, payload, context)


def test_dispatch_failure_falls_back_and_run_continues(tmp_path):
    engine = agent_run("agents", tmp_path, backend=BrokenDispatch())
    fallbacks = engine.log.of_type(EventType.FALLBACK_USED)
    assert fallbacks and any("dispatch failed" in e.payload["reason"] for e in fallbacks)
    assert engine.tick == engine.end_tick


def test_no_negotiation_never_calls_allocator(tmp_path):
    engine = agent_run("agents_no_negotiation", tmp_path, negotiate=False)
    agents_called = {e.payload["agent"] for e in engine.log.of_type(EventType.LLM_CALL)}
    assert "allocator" not in agents_called and "dispatch" in agents_called
    assert not [e for e in engine.log.of_type(EventType.MESSAGE)
                if e.payload["type"] == "RESOLVE"]


def test_llm_calls_are_bounded(tmp_path):
    engine = agent_run("agents", tmp_path, hook=False)
    assert len(engine.log.of_type(EventType.LLM_CALL)) < 400


# --- confidence and approval ---------------------------------------------------------------------

def test_confidence_components(surge_obs):
    obs = obs_with(surge_obs, lambda o: any(
        o.patient(pid) and o.patient(pid).severity == "CRITICAL"
        for u in o.units_needing_destination() for pid in u.patient_ids))
    unit = next(u for u in obs.units_needing_destination()
                if any(obs.patient(p).severity == "CRITICAL" for p in u.patient_ids))
    pats = [obs.patient(p) for p in unit.patient_ids]
    c = score(obs, unit.id, "A", pats)
    assert 0 <= c.score <= 1 and 0 <= c.freshness <= 1
    dirty = score(obs, unit.id, "A", pats, validator_clean=False)
    assert dirty.score == pytest.approx(c.score - 0.1, abs=1e-6)
    fresh = score(obs, unit.id, "A", pats, live_free=obs.own_status["A"]["free"])
    assert fresh.freshness == 1.0


def test_r6_review_is_held_then_approved_for_baselines_too():
    engine = Engine(generate(7, "surge"), RuleBasedPolicy())
    engine.run()
    esc = engine.log.of_type(EventType.ESCALATED)
    done = engine.log.of_type(EventType.APPROVED) + engine.log.of_type(EventType.OVERRIDDEN)
    assert esc and len(done) == len(esc)
    by_id = {e.payload["approval_id"]: e.tick for e in esc}
    for e in done:
        assert e.tick - by_id[e.payload["approval_id"]] == 2  # 2-minute policy delay
        assert e.payload["approver"] == "policy"


def test_interactive_approval_takes_human_choice():
    engine = Engine(generate(7, "surge"), RuleBasedPolicy(), approval_mode="interactive")
    while not engine.pending_approvals and engine.tick < engine.end_tick:
        engine.step()
    pending = engine.pending_approvals[0]
    engine.decide_approval(pending.id, "approve")
    engine.step()
    approved = engine.log.of_type(EventType.APPROVED)
    assert approved and approved[0].payload["approver"] == "human"


def test_needs_review_flag_escalates_any_action():
    from sim.actions import Dispatch
    engine = Engine(generate(7, "surge"), None)
    engine.run(until=36)
    pid = next(p for p in engine.incidents["MCI-2"].true_victim_ids
               if engine.patients[p].true_severity == "SERIOUS")
    unit = next(a.id for a in engine.ambulances.values() if a.state == "IDLE"
                and engine.unit_available(a.id))
    assert engine.commit(Dispatch(unit_id=unit, incident_id="MCI-2", patient_ids=[pid]))
    while not engine.units_needing_destination():
        engine.step()
    assert engine.commit(RouteToHospital(unit_id=unit, hospital_id="A", needs_review=True,
                                         confidence=0.5))
    assert engine.pending_approvals and engine.pending_approvals[0].action.unit_id == unit
    engine.step()
    engine.step()
    assert engine.log.of_type(EventType.APPROVED) or engine.log.of_type(EventType.OVERRIDDEN)


def test_failed_call_is_cached_and_replays_as_failure(tmp_path):
    from orca_agents.llm_cache import AgentSpec, LLMClient, RecordedFailure
    from orca_agents.models import PriorityReport

    class Broken:
        model = "broken"

        def run(self, spec, payload, context):
            raise RuntimeError("model gave up")

    spec = AgentSpec("assessment", "assessment.md", PriorityReport)
    live = LLMClient(Broken(), mode="live", cache_dir=tmp_path)
    with pytest.raises(RuntimeError):
        live.call(spec, {"x": 1})
    replay = LLMClient(None, mode="cache_only", cache_dir=tmp_path, model_name="broken")
    with pytest.raises(RecordedFailure, match="model gave up"):
        replay.call(spec, {"x": 1})


def test_assigning_a_crew_to_the_call_it_already_serves_is_a_no_op(tmp_path):
    from baselines.nearest import NearestPolicy
    from orca_agents.models import Assignment, DispatchPlan

    engine = Engine(generate(7, "surge"), NearestPolicy())
    engine.initialize()
    while not any(u.state == "EN_ROUTE" for u in engine.observe().units.values()):
        engine.step()
    obs = engine.observe()
    unit = next(u for u in obs.units.values() if u.state == "EN_ROUTE")
    plan = DispatchPlan(assignments=[Assignment(unit_id=unit.id,
                                                incident_id=unit.assigned_incident,
                                                patient_ids=[], rationale="same call")],
                        rationale="")
    actions, conflicts = AgentPolicy(client=client(tmp_path))._assignments(obs, plan)
    assert not actions and not conflicts
