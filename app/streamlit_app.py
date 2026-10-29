"""ORCA-EMS dispatch dashboard.

    streamlit run app/streamlit_app.py

Pick an incident, press Start, and watch how it is handled: the incident table, map, and the
conversation between caller, dispatch, ambulances, hospitals, and the safety rules. Everything
on screen is rebuilt from the event log, so a saved run replays exactly.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # `streamlit run` puts app/ on the path, not the repo root
    sys.path.insert(0, str(ROOT))

import config.settings as settings  # noqa: E402
from app import panels  # noqa: E402
from app.map_view import town_map  # noqa: E402
from app.state import build_state  # noqa: E402
from baselines.nearest import NearestPolicy  # noqa: E402
from baselines.rule_based import RuleBasedPolicy  # noqa: E402
from config.settings import LOG_DIR  # noqa: E402
from sim.engine import Engine  # noqa: E402
from sim.events import read_jsonl  # noqa: E402
from sim.generator import DEFAULT_POPULATION  # noqa: E402
from sim.presets import PRESETS, build_preset  # noqa: E402
from sim.town import TownProfile  # noqa: E402


def _agents(negotiate: bool, offline: bool):
    def make():
        from orca_agents.llm_cache import LLMClient
        from orca_agents.orchestrator import AgentPolicy, default_client
        if offline:
            from orca_agents.scripted import ScriptedBackend
            return AgentPolicy(negotiate, LLMClient(ScriptedBackend(), mode="live",
                                                    cache_dir=LOG_DIR / "dashboard_cache"))
        return AgentPolicy(negotiate, default_client())
    return make


HAVE_LLM = bool(os.getenv("OPENAI_API_KEY") and settings.OPENAI_MODEL)
POLICIES = {"Nearest hospital (baseline)": NearestPolicy,
            "Rule-based (strong baseline)": RuleBasedPolicy}
if HAVE_LLM:
    POLICIES["AI agents, negotiating (OpenAI)"] = _agents(True, False)
    POLICIES["AI agents, no negotiation (OpenAI)"] = _agents(False, False)
POLICIES["AI agents, negotiating (offline stand-in)"] = _agents(True, True)

st.set_page_config(page_title="ORCA-EMS Dispatch", layout="wide",
                   initial_sidebar_state="collapsed")
panels.inject_css()
ss = st.session_state
ss.setdefault("playing", False)
ss.setdefault("focus", "All incidents")
ss.setdefault("preset", "School bus crash")


def new_engine() -> None:
    cfg = (ss.get("preset", "School bus crash"), int(ss.get("seed", 7)),
           int(ss.get("population", DEFAULT_POPULATION)),
           ss.get("policy", next(iter(POLICIES))))
    mode = "interactive" if ss.get("human_approval") else "policy"
    ss.engine = Engine(build_preset(cfg[0], cfg[1], cfg[2]), POLICIES[cfg[3]](),
                       approval_mode=mode)
    ss.engine.initialize()
    ss.config = cfg
    ss.playing = False
    ss.focus = "All incidents"


def toggle_play() -> None:
    if ss.engine.tick >= ss.engine.end_tick:
        new_engine()
    ss.playing = not ss.playing


def step(minutes: int) -> None:
    ss.playing = False
    ss.engine.run(until=ss.engine.tick + minutes)


# --- Advanced (sidebar, collapsed by default) -------------------------------------------------
with st.sidebar:
    st.markdown("### Advanced")
    st.caption("For experiments. Viewers do not need these.")
    st.number_input("Seed (variation of the same incident)", 0, 999, 7, key="seed",
                    on_change=new_engine)
    st.number_input("Town population", 10_000, 1_000_000, DEFAULT_POPULATION, step=10_000,
                    key="population", on_change=new_engine)
    st.toggle("I approve risky decisions myself", key="human_approval", on_change=new_engine,
              help="Decisions flagged for human review pause the run and wait for you. "
                   "Off: a fixed approval policy decides after 2 simulated minutes.")
    if not HAVE_LLM:
        st.caption("No OpenAI key in .env: the agents run with an offline stand-in that "
                   "follows their instructions with simple rules. It is not an LLM.")
    st.slider("Speed (simulated minutes per second)", 1, 15, 3, key="speed")
    replay = st.toggle("Replay a saved run", key="replay_mode")
    if st.button("Save this run", use_container_width=True) and "engine" in ss:
        path = ss.engine.log.write_jsonl(LOG_DIR / f"run_{ss.engine.run_id}.jsonl")
        st.success(f"Saved {path.name}")
    if replay:
        logs = sorted(LOG_DIR.glob("run_*.jsonl"))
        choice = st.selectbox("Saved run", logs, format_func=lambda p: p.name, key="replay_file")
        if choice is not None and ss.get("replay_path") != str(choice):
            ss.replay_events = read_jsonl(choice)
            ss.replay_path = str(choice)
            ss.replay_tick = 0

if "engine" not in ss:
    new_engine()

# --- top bar ----------------------------------------------------------------------------------
st.markdown("### ORCA-EMS · Dispatch")
pick, who = st.columns([1, 1], vertical_alignment="bottom")
pick.selectbox("Incident", list(PRESETS), key="preset", on_change=new_engine)
who.selectbox("Who makes the decisions", list(POLICIES), key="policy", on_change=new_engine)
b1, b2, b3, b4 = st.columns(4, vertical_alignment="bottom")
b1.button("Pause" if ss.playing else "Start", type="primary", use_container_width=True,
          on_click=toggle_play)
b2.button("+1 min", use_container_width=True, on_click=step, args=(1,))
b3.button("+15 min", use_container_width=True, on_click=step, args=(15,))
b4.button("Reset", use_container_width=True, on_click=new_engine)
st.caption(PRESETS[ss.get("preset", "School bus crash")].description +
           " · Town of 50,000 on a 20 × 20 km grid")


def approval_cards() -> None:
    """Interactive approval (PLAN §14.6): top option vs the best alternative."""
    engine = ss.get("engine")
    if engine is None or ss.get("replay_mode") or engine.approval_mode != "interactive":
        return
    for p in engine.pending_approvals:
        if p.decided:
            continue
        a, alt = p.action, p.alternative
        target = getattr(a, "hospital_id", None) or getattr(a, "incident_id", "")
        with st.container(border=True):
            st.markdown(f"**Needs your approval · {p.id}** — {a.unit_id} → "
                        f"{'Hospital ' + target if getattr(a, 'hospital_id', None) else target}")
            for r in p.reasons:
                st.caption(r)
            if getattr(a, "confidence", None) is not None:
                st.caption(f"Agent confidence: {a.confidence:.2f}")
            c1, c2 = st.columns(2)
            c1.button("Approve", key=f"ok_{p.id}", type="primary", use_container_width=True,
                      on_click=engine.decide_approval, args=(p.id, "approve"))
            if alt is not None:
                c2.button(f"Use Hospital {alt.hospital_id}", key=f"alt_{p.id}",
                          use_container_width=True, on_click=engine.decide_approval,
                          args=(p.id, "alternative"))


def render(events, tick, timings) -> None:
    state = build_state(events, upto=tick)
    chips, clock = st.columns([6, 1], vertical_alignment="center")
    with chips:
        panels.status_chips(state)
    clock.markdown(panels.clock_html(tick), unsafe_allow_html=True)
    options = ["All incidents"] + sorted(state.incidents)
    if ss.focus not in options:
        ss.focus = "All incidents"
    focus_id = None if ss.focus == "All incidents" else ss.focus
    town = TownProfile(population=state.run.get("population") or DEFAULT_POPULATION)

    panels.ai_banner(state, ss.config[3] if "config" in ss else "")
    panels.incident_table(state, focus_id)
    side, main = st.columns([1, 3.4], gap="medium")
    with side:
        layers = panels.map_sidebar(state, town.population, town.area_km)
    with main:
        st.plotly_chart(town_map(state, town, focus_id, height=660, layers=layers),
                        use_container_width=True, config={"displayModeBar": False})

    left, right = st.columns([1.15, 1], gap="medium")
    with left:
        approval_cards()
        st.selectbox("Show conversation for", options, key="focus")
        panels.conversation(state, focus_id, height=460)
    with right:
        st.markdown('<div class="cad-h">Ambulances</div>', unsafe_allow_html=True)
        panels.unit_board(state)

    panels.hospital_board(state)
    tabs = st.tabs(["AI activity", "Mass-casualty board", "Timeline and handling time"])
    with tabs[0]:
        panels.ai_activity(state)
    with tabs[1]:
        panels.mci_board(state)
    with tabs[2]:
        panels.timeline(state, events, timings, focus_id)


if ss.get("replay_mode") and ss.get("replay_events"):
    events = ss.replay_events
    ss.replay_tick = st.slider("Replay minute", 0, events[-1].tick, ss.get("replay_tick", 0))
    render(events, ss.replay_tick, [])
else:
    @st.fragment(run_every=1.0 if ss.playing else None)
    def live_view() -> None:
        engine: Engine = ss.engine
        if ss.playing:
            for _ in range(ss.speed):
                engine.run(until=engine.tick + 1)
                if engine.approval_mode == "interactive" and any(
                        not p.decided for p in engine.pending_approvals):
                    ss.playing = False  # wait for the human
                    st.rerun(scope="app")
            if engine.tick >= engine.end_tick:
                ss.playing = False
                st.rerun(scope="app")
        render(engine.log.events, engine.tick, engine.decision_timings)

    live_view()
