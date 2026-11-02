"""V2 must preserve engine data, source attribution, and safe playback controls."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.state import build_state as shared_state
from baselines.rule_based import RuleBasedPolicy
from dashboard_v2.state import build_state, wall_clock
from orca_agents.llm_cache import LLMClient
from orca_agents.orchestrator import AgentPolicy
from orca_agents.scripted import ScriptedBackend
from sim.engine import Engine
from sim.presets import build_preset


@pytest.mark.parametrize("minute", [0, 15, 90])
def test_v2_preserves_shared_projection(minute):
    engine = Engine(build_preset("School bus crash"), RuleBasedPolicy())
    engine.run(until=90)
    expected = shared_state(engine.log.events, upto=minute)
    actual = build_state(engine.log.events, upto=minute)
    assert actual.hospitals == expected.hospitals
    assert actual.units == expected.units
    assert actual.patients == expected.patients
    assert actual.feed == expected.feed
    assert all(actual.kpis[k] == value for k, value in expected.kpis.items())
    assert all(r.tick <= minute for r in actual.feed)


def test_scripted_calls_keep_explanation_and_source(tmp_path):
    client = LLMClient(ScriptedBackend(), mode="live", cache_dir=tmp_path)
    engine = Engine(build_preset("Cardiac arrest"), AgentPolicy(client=client))
    engine.run(until=60)
    state = build_state(engine.log.events)
    assert state.agent_decisions
    assert all(d["source"] == "standin" for d in state.agent_decisions)
    assert any(d["explanation"] for d in state.agent_decisions)
    assert "standin" in {r.source for r in state.feed}
    assert "ai" not in {r.source for r in state.feed}


def test_dashboard_advance_focus_and_reset():
    at = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "dashboard_v2/streamlit_app.py"
    ).run(timeout=30)
    assert not at.exception
    advance = next(b for b in at.button if b.label == "Advance 15 min")
    advance.click().run(timeout=30)
    assert not at.exception
    assert at.session_state["v2_engine"].tick == 15
    at.selectbox(key="v2_focus").select("I-CARDIAC").run(timeout=30)
    assert not at.exception
    next(b for b in at.button if b.label == "Reset run").click().run(timeout=30)
    assert not at.exception
    assert at.session_state["v2_engine"].tick == 0
    assert at.session_state["v2_focus"] == "All incidents"


def test_replay_uses_saved_log_and_disables_live_controls(tmp_path, monkeypatch):
    import config.settings as settings
    import eval.run_report as report

    engine = Engine(build_preset("Cardiac arrest"), RuleBasedPolicy())
    engine.run(until=15)
    engine.log.write_jsonl(tmp_path / "example" / "events.jsonl")
    monkeypatch.setattr(report, "SAVE_DIR", tmp_path)
    monkeypatch.setattr(settings, "LOG_DIR", tmp_path)
    at = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "dashboard_v2/streamlit_app.py"
    ).run(timeout=30)
    at.toggle(key="v2_replay").set_value(True).run(timeout=30)
    assert not at.exception
    assert all(
        b.disabled
        for b in at.button
        if b.label in ("Start simulation", "Advance 15 min", "Reset run")
    )
    end = max(e.tick for e in engine.log.events)
    at.slider[0].set_value(end).run(timeout=30)
    assert not at.exception
    assert at.session_state["v2_engine"].tick == 0
    assert any(wall_clock(end) in m.value and "Replay" in m.value for m in at.markdown)


def test_manual_advance_stops_for_human_review():
    at = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "dashboard_v2/streamlit_app.py"
    ).run(timeout=30)
    at.toggle(key="v2_human").set_value(True).run(timeout=30)
    engine = at.session_state["v2_engine"]
    # Use the engine's public approval queue to verify that a pending review is a barrier.
    from types import SimpleNamespace

    engine.pending_approvals.append(
        SimpleNamespace(
            id="test-review",
            decided=False,
            reasons=["Review this destination"],
            action=SimpleNamespace(unit_id="AMB-1", hospital_id="A", confidence=0.7),
            alternative=None,
        )
    )
    next(b for b in at.button if b.label == "Advance 15 min").click().run(timeout=30)
    assert not at.exception
    assert at.session_state["v2_engine"].tick == 0
    assert any(b.label == "Approve proposal" for b in at.button)


def test_workspace_navigation_with_mass_casualty_run():
    at = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "dashboard_v2/streamlit_app.py"
    ).run(timeout=30)
    at.selectbox(key="v2_preset").select("School bus crash").run(timeout=30)
    next(b for b in at.button if b.label == "Advance 15 min").click().run(timeout=30)
    for page in ["Hospital network", "Decision room", "Run report", "Response overview"]:
        at.radio(key="v2_page").set_value(page).run(timeout=30)
        assert not at.exception
    assert at.session_state["v2_engine"].tick == 15
    assert at.session_state["v2_preset"] == "School bus crash"


def test_incident_focus_survives_other_workspaces():
    at = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "dashboard_v2/streamlit_app.py"
    ).run(timeout=30)
    next(b for b in at.button if b.label == "Advance 15 min").click().run(timeout=30)
    at.selectbox(key="v2_focus").select("I-CARDIAC").run(timeout=30)
    for destination in ["Hospital network", "Ambulance fleet", "Run report", "Decision room"]:
        at.radio(key="v2_page").set_value(destination).run(timeout=30)
        assert not at.exception
        assert at.session_state["v2_selected"] == "I-CARDIAC"
    assert at.selectbox(key="v2_focus").value == "I-CARDIAC"


def test_guided_demo_is_offline_and_preserves_live_run(tmp_path, monkeypatch):
    import config.settings as settings
    from orca_agents.llm_cache import OpenAIAgentsBackend

    def no_network(*args, **kwargs):
        pytest.fail("Guided demo must never invoke a model backend")

    monkeypatch.setattr(OpenAIAgentsBackend, "run", no_network)
    monkeypatch.setattr(settings, "LOG_DIR", tmp_path)
    at = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "dashboard_v2/streamlit_app.py"
    ).run(timeout=30)
    next(b for b in at.button if b.label == "Advance 15 min").click().run(timeout=30)
    live_events = list(at.session_state["v2_engine"].log.events)
    at.button(key="v2_demo_start").click().run(timeout=30)
    assert not at.exception
    assert at.session_state["v2_demo_active"]
    demo = at.session_state["v2_demo"]
    calls = [e for e in demo.events if e.type.value == "LLM_CALL"]
    assert calls and all(e.payload["model"] == "scripted" for e in calls)
    assert [c.tick for c in demo.chapters] == sorted(c.tick for c in demo.chapters)
    for index in range(1, 5):
        at.button(key="v2_demo_next").click().run(timeout=30)
        assert not at.exception
        assert at.session_state["v2_demo_index"] == index
        assert at.radio(key="v2_page").value == demo.chapters[index].page
    assert at.button(key="v2_demo_next").disabled
    assert not any(b.label == "Save run & scorecard" for b in at.button)
    at.button(key="v2_demo_previous").click().run(timeout=30)
    assert at.session_state["v2_demo_index"] == 3
    at.button(key="v2_demo_exit").click().run(timeout=30)
    assert not at.exception
    assert not at.session_state["v2_demo_active"]
    assert at.session_state["v2_engine"].tick == 15
    assert at.session_state["v2_engine"].log.events == live_events


def test_overview_shortcut_opens_decision_room():
    at = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "dashboard_v2/streamlit_app.py"
    ).run(timeout=30)
    at.button(key="v2_full_trail").click().run(timeout=30)
    assert not at.exception
    assert at.radio(key="v2_page").value == "Decision room"


def test_guided_demo_can_explore_and_return(tmp_path, monkeypatch):
    import config.settings as settings

    monkeypatch.setattr(settings, "LOG_DIR", tmp_path)
    at = AppTest.from_file(
        Path(__file__).resolve().parents[1] / "dashboard_v2/streamlit_app.py"
    ).run(timeout=30)
    at.button(key="v2_quick_demo").click().run(timeout=30)
    assert not at.exception
    at.radio(key="v2_page").set_value("Ambulance fleet").run(timeout=30)
    at.radio(key="v2_fleet_filter").set_value("Standby").run(timeout=30)
    assert not at.exception
    at.button(key="v2_demo_return").click().run(timeout=30)
    assert at.radio(key="v2_page").value == "Response overview"
    assert at.session_state["v2_demo_index"] == 0
