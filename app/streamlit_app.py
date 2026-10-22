"""ORCA-EMS dispatch dashboard.

    streamlit run app/streamlit_app.py

Pick an incident, press Start, and watch how it is handled: the incident table, map, and the
conversation between caller, dispatch, ambulances, hospitals, and the safety rules. Everything
on screen is rebuilt from the event log, so a saved run replays exactly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # `streamlit run` puts app/ on the path, not the repo root
    sys.path.insert(0, str(ROOT))

from app import panels  # noqa: E402
from app.map_view import town_map  # noqa: E402
from app.state import build_state  # noqa: E402
from baselines.nearest import NearestPolicy  # noqa: E402
from config.settings import LOG_DIR  # noqa: E402
from sim.engine import Engine  # noqa: E402
from sim.events import read_jsonl  # noqa: E402
from sim.generator import DEFAULT_POPULATION  # noqa: E402
from sim.presets import PRESETS, build_preset  # noqa: E402
from sim.town import TownProfile  # noqa: E402

POLICIES = {"Nearest hospital (baseline)": NearestPolicy}

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
    ss.engine = Engine(build_preset(cfg[0], cfg[1], cfg[2]), POLICIES[cfg[3]]())
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
    st.selectbox("Who makes the decisions", list(POLICIES), key="policy", on_change=new_engine,
                 help="The LLM agents join this list in milestones M6–M7.")
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
pick, b1, b2, b3, b4 = st.columns([3, 1, 1, 1, 1], vertical_alignment="bottom")
pick.selectbox("Incident", list(PRESETS), key="preset", on_change=new_engine,
               label_visibility="collapsed")
b1.button("Pause" if ss.playing else "Start", type="primary", use_container_width=True,
          on_click=toggle_play)
b2.button("+1 min", use_container_width=True, on_click=step, args=(1,))
b3.button("+15 min", use_container_width=True, on_click=step, args=(15,))
b4.button("Reset", use_container_width=True, on_click=new_engine)
st.caption(PRESETS[ss.get("preset", "School bus crash")].description +
           " · Town of 50,000 on a 20 × 20 km grid · decisions by "
           f"{ss.get('policy', next(iter(POLICIES))).lower()}")


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

    panels.incident_table(state, focus_id)
    left, right = st.columns([1, 1.1], gap="medium")
    with left:
        st.markdown('<div class="cad-h">Town map (km grid)</div>', unsafe_allow_html=True)
        st.plotly_chart(town_map(state, town, focus_id, height=420), use_container_width=True,
                        config={"displayModeBar": False})
    with right:
        st.selectbox("Show conversation for", options, key="focus")
        panels.conversation(state, focus_id, height=440)

    panels.hospital_board(state)
    tabs = st.tabs(["Ambulances", "Mass-casualty board", "Timeline and handling time"])
    with tabs[0]:
        panels.unit_board(state)
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
            engine.run(until=engine.tick + ss.speed)
            if engine.tick >= engine.end_tick:
                ss.playing = False
                st.rerun(scope="app")
        render(engine.log.events, engine.tick, engine.decision_timings)

    live_view()
