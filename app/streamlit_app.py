"""ORCA-EMS live dashboard.

    streamlit run app/streamlit_app.py

Live mode runs a scenario tick by tick in this process; replay mode reads a saved log.
Everything on screen is rebuilt from the event log, so live and replay look the same.
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
from sim.generator import DEFAULT_POPULATION, generate  # noqa: E402
from sim.town import TownProfile  # noqa: E402

POLICIES = {"nearest (baseline)": NearestPolicy}

st.set_page_config(page_title="ORCA-EMS Live", layout="wide", page_icon="🚑")
panels.inject_css()
ss = st.session_state


def new_engine(seed: int, demand: str, population: int, policy: str) -> None:
    ss.engine = Engine(generate(seed, demand, population), POLICIES[policy]())
    ss.engine.initialize()
    ss.playing = False
    ss.config = (seed, demand, population, policy)


# --- sidebar ------------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ORCA-EMS")
    st.caption("Orchestrated Response and Capacity Allocation")
    mode = st.radio("Mode", ["Live", "Replay"], horizontal=True, key="mode")
    if mode == "Live":
        seed = st.number_input("Seed", 0, 999, 7, key="seed")
        demand = st.selectbox("Demand", ["surge", "normal"], key="demand")
        population = st.number_input("Population", 10_000, 1_000_000, DEFAULT_POPULATION,
                                     step=10_000, key="population")
        policy = st.selectbox("Policy", list(POLICIES), key="policy",
                              help="LLM agents are added here in milestones M6–M7.")
        speed = st.slider("Speed (sim minutes per second)", 1, 15, 3, key="speed")
        config = (int(seed), demand, int(population), policy)
        if "engine" not in ss or ss.get("config") != config:
            new_engine(*config)
        c1, c2 = st.columns(2)
        c1.button("Pause" if ss.playing else "Play", use_container_width=True, type="primary",
                  on_click=lambda: ss.update(playing=not ss.playing))
        c2.button("Reset", use_container_width=True, on_click=new_engine, args=config)
        c3, c4 = st.columns(2)
        if c3.button("+1 min", use_container_width=True):
            ss.engine.run(until=ss.engine.tick + 1)
        if c4.button("+15 min", use_container_width=True):
            ss.engine.run(until=ss.engine.tick + 15)
        if st.button("Save log", use_container_width=True):
            path = ss.engine.log.write_jsonl(LOG_DIR / f"run_{ss.engine.run_id}.jsonl")
            st.success(f"Saved {path.name}")
    else:
        logs = sorted(LOG_DIR.glob("run_*.jsonl"))
        if not logs:
            st.warning("No saved runs in logs/. Use Live mode and press Save log.")
        choice = st.selectbox("Saved run", logs, format_func=lambda p: p.name, key="replay_file")
        speed = st.slider("Speed (sim minutes per second)", 1, 15, 5, key="replay_speed")
        if choice is not None and ss.get("replay_path") != str(choice):
            ss.replay_events = read_jsonl(choice)
            ss.replay_path = str(choice)
            ss.replay_tick = 0
            ss.replay_playing = False
        if choice is not None:
            end = ss.replay_events[-1].tick
            st.button("Pause" if ss.replay_playing else "Play", use_container_width=True,
                      type="primary",
                      on_click=lambda: ss.update(replay_playing=not ss.replay_playing))
            ss.replay_tick = st.slider("Minute", 0, end, ss.replay_tick)


# --- main view (refreshes itself while playing) --------------------------------------------------
def render(events, tick, timings, population) -> None:
    state = build_state(events, upto=tick)
    town = TownProfile(population=population)
    t = state.run.get("town") or {}
    st.markdown(
        f"#### {state.run.get('demand', '').title()} scenario · seed {state.run.get('seed')} · "
        f"{population:,} people on {town.area_km:g} × {town.area_km:g} km · policy "
        f"`{state.run.get('policy')}`")
    if t:
        st.caption(
            f"Derived town: {t.get('city_ambulances')} city + {t.get('private_units')} private "
            f"ambulances · {t.get('calls_per_hour')} calls/h · {t.get('staffed_beds')} staffed "
            f"beds · {t.get('physicians_on_duty')} physicians and "
            f"{t.get('hospital_nurses_on_duty')} hospital nurses on duty "
            "(from U.S. per-capita ratios; see ASSUMPTIONS.md)")
    panels.kpi_bar(state)
    left, right = st.columns([3, 2], gap="medium")
    with left:
        st.plotly_chart(town_map(state, town), use_container_width=True,
                        config={"displayModeBar": False})
    with right:
        st.markdown("**Hospital capacity (live)**")
        panels.hospital_cards(state)
    tabs = st.tabs(["Calls and agent messages", "All messages", "Handling time", "Ambulances"])
    with tabs[0]:
        panels.call_threads(state)
    with tabs[1]:
        panels.message_feed(state)
    with tabs[2]:
        panels.handling_tab(state, events, timings)
    with tabs[3]:
        panels.units_table(state)


if mode == "Live":
    @st.fragment(run_every=1.0 if ss.playing else None)
    def live_view() -> None:
        engine: Engine = ss.engine
        if ss.playing:
            engine.run(until=engine.tick + ss.speed)
            if engine.tick >= engine.end_tick:
                ss.playing = False
                st.rerun(scope="app")
        render(engine.log.events, engine.tick, engine.decision_timings,
               engine.scenario.population or DEFAULT_POPULATION)

    live_view()
elif ss.get("replay_events"):
    @st.fragment(run_every=1.0 if ss.replay_playing else None)
    def replay_view() -> None:
        events = ss.replay_events
        if ss.replay_playing:
            ss.replay_tick = min(events[-1].tick, ss.replay_tick + ss.replay_speed)
            if ss.replay_tick >= events[-1].tick:
                ss.replay_playing = False
        started = next((e.payload for e in events if e.type == "RUN_STARTED"), {})
        render(events, ss.replay_tick, [],
               (started.get("town") or {}).get("population", DEFAULT_POPULATION))

    replay_view()
