"""ORCA Emergency Command. Run: streamlit run dashboard_v2/streamlit_app.py."""

from __future__ import annotations

import html
import os
import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config.settings as settings  # noqa: E402
from app.map_view import LAYERS  # noqa: E402
from baselines.nearest import NearestPolicy  # noqa: E402
from baselines.rule_based import RuleBasedPolicy  # noqa: E402
from dashboard_v2 import workspace as ui  # noqa: E402
from dashboard_v2.map_view import response_map  # noqa: E402
from dashboard_v2.state import build_state, wall_clock  # noqa: E402
from sim.engine import Engine  # noqa: E402
from sim.events import read_jsonl  # noqa: E402
from sim.generator import DEFAULT_POPULATION  # noqa: E402
from sim.presets import PRESETS, build_preset  # noqa: E402
from sim.town import TownProfile  # noqa: E402


def agent_factory(negotiate: bool, offline: bool):
    def make():
        from orca_agents.llm_cache import LLMClient
        from orca_agents.orchestrator import AgentPolicy, default_client
        from orca_agents.scripted import ScriptedBackend

        client = (
            LLMClient(ScriptedBackend(), mode="live", cache_dir=settings.LOG_DIR / "v2_cache")
            if offline
            else default_client()
        )
        return AgentPolicy(negotiate, client)

    return make


POLICIES = {"Rule-based dispatch": RuleBasedPolicy, "Nearest hospital": NearestPolicy}
try:
    from orca_agents.orchestrator import AgentPolicy as _AgentPolicy  # noqa: F401
except ImportError:
    pass
else:
    POLICIES["Scripted agents · offline"] = agent_factory(True, True)
    if settings.OPENAI_MODEL and (os.getenv("OPENAI_API_KEY") or settings.LLM_MODE == "cache_only"):
        mode = "cached" if settings.LLM_MODE == "cache_only" else "OpenAI"
        POLICIES[f"AI agents + negotiation · {mode}"] = agent_factory(True, False)
        POLICIES[f"AI agents, no negotiation · {mode}"] = agent_factory(False, False)

PACE = {
    "1 simulated min / sec": 1.0,
    "5 simulated min / sec": 5.0,
    "15 simulated min / sec": 15.0,
    "Real time": 1 / 60,
}

st.set_page_config(
    page_title="ORCA | Emergency Command",
    page_icon="🚑",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    f"<style>{Path(__file__).with_name('styles.css').read_text()}</style>", unsafe_allow_html=True
)
ss = st.session_state
# Prefix state so opening v1 and v2 does not reuse incompatible engines/settings.
ss.setdefault("v2_playing", False)
ss.setdefault("v2_focus", "All incidents")
ss.setdefault("v2_preset", next(iter(PRESETS)))
ss.setdefault("v2_policy", next(iter(POLICIES)))
ss.setdefault("v2_pace", next(iter(PACE)))
ss.setdefault("v2_demo_active", False)
ss.setdefault("v2_selected", "All incidents")
ss.setdefault("v2_present", False)
NAVIGATION = [
    "Response overview",
    "Hospital network",
    "Ambulance fleet",
    "Decision room",
    "Run report",
]
PAGE_HELP = {
    "Response overview": "Find calls on the map, inspect a patient response, and check capacity.",
    "Hospital network": "Compare beds, hospital capabilities, and patient distribution.",
    "Ambulance fleet": "Find every unit, its assignment, destination, and time in status.",
    "Decision room": "See who proposed each action, what hospitals replied, and its source.",
    "Run report": "Review response times, outcomes, and save or download this run.",
}


def new_engine() -> None:
    cfg = (
        ss.v2_preset,
        int(ss.get("v2_seed", 7)),
        int(ss.get("v2_population", DEFAULT_POPULATION)),
        ss.v2_policy,
    )
    ss.v2_engine = Engine(
        build_preset(cfg[0], cfg[1], cfg[2]),
        POLICIES[cfg[3]](),
        approval_mode="interactive" if ss.get("v2_human") else "policy",
    )
    ss.v2_engine.initialize()
    ss.v2_config = cfg
    ss.v2_playing = False
    ss.v2_focus = "All incidents"
    ss.v2_selected = "All incidents"
    ss.v2_budget = 0.0


def toggle_play() -> None:
    if ss.v2_engine.tick >= ss.v2_engine.end_tick:
        new_engine()
    ss.v2_playing = not ss.v2_playing
    ss.v2_last_wall = time.monotonic()
    ss.v2_budget = 0.0


def step(minutes: int) -> None:
    ss.v2_playing = False
    # Stop at every approval barrier, including when advancing manually.
    for _ in range(minutes):
        if needs_review(ss.v2_engine):
            break
        if ss.v2_engine.tick >= ss.v2_engine.end_tick:
            break
        ss.v2_engine.run(until=ss.v2_engine.tick + 1)


def save_current(note: bool = True) -> None:
    from eval.run_report import save_run

    folder = save_run(ss.v2_engine.log.events, ss.v2_config[0])
    if note:
        st.toast(f"Run saved: {folder.name}")


def stop_playback() -> None:
    ss.v2_playing = False


def needs_review(engine: Engine) -> bool:
    return engine.approval_mode == "interactive" and any(
        not p.decided for p in engine.pending_approvals
    )


def navigate(destination: str) -> None:
    ss.v2_page = destination


def remember_focus() -> None:
    ss.v2_selected = ss.v2_focus


def start_demo() -> None:
    from dashboard_v2.demo import build_demo

    ss.v2_playing = False
    if "v2_demo" not in ss:
        with st.spinner("Preparing the offline walkthrough…"):
            ss.v2_demo = build_demo(settings.LOG_DIR / "v2_demo_cache")
    if not ss.v2_demo_active:
        ss.v2_before_demo_focus = ss.v2_selected
        ss.v2_before_demo_present = ss.v2_present
    ss.v2_demo_active = True
    ss.v2_replay = False
    ss.v2_demo_index = 0
    ss.v2_page = "Response overview"
    ss.v2_focus = ss.v2_selected = "All incidents"
    ss.v2_present = True


def demo_step(change: int) -> None:
    index = max(0, min(len(ss.v2_demo.chapters) - 1, ss.v2_demo_index + change))
    ss.v2_demo_index = index
    chapter = ss.v2_demo.chapters[index]
    ss.v2_page = chapter.page
    ss.v2_focus = ss.v2_selected = chapter.focus or "All incidents"


def leave_demo() -> None:
    ss.v2_demo_active = False
    ss.v2_page = "Response overview"
    ss.v2_focus = ss.v2_selected = ss.get("v2_before_demo_focus", "All incidents")
    ss.v2_present = ss.get("v2_before_demo_present", False)


def incident_picker(state, *, collapsed: bool = False) -> None:
    options = ["All incidents", *sorted(state.incidents)]
    if ss.v2_selected not in options:
        ss.v2_selected = "All incidents"
    ss.v2_focus = ss.v2_selected

    def label(iid):
        if iid == "All incidents":
            return "All incidents"
        incident = state.incidents[iid]
        kind = incident["type"].replace("_", " ").title()
        return f"{kind} · {iid} · {incident['waiting']} waiting"

    st.selectbox(
        "Find an incident",
        options,
        key="v2_focus",
        format_func=label,
        on_change=remember_focus,
        label_visibility="collapsed" if collapsed else "visible",
        help="Type an emergency name or incident ID to find it.",
    )


if "v2_engine" not in ss:
    new_engine()

with st.sidebar:
    ui.markup(
        '<div class="rail-brand"><div class="rail-logo">✚</div><div>'
        '<div class="rail-name">ORCA</div><div class="rail-sub">Emergency coordination</div>'
        '</div></div><div class="rail-label">WORKSPACE</div>'
    )
    page = st.radio(
        "Workspace",
        NAVIGATION,
        key="v2_page",
        label_visibility="collapsed",
    )
    st.caption(PAGE_HELP[page])
    st.button(
        "Restart guided demo" if ss.v2_demo_active else "Start guided demo",
        key="v2_demo_start",
        on_click=start_demo,
        use_container_width=True,
        help="Five paused checkpoints. Runs offline with scripted agents.",
    )
    if ss.v2_demo_active:
        st.button(
            "Exit demo · return to my run",
            on_click=leave_demo,
            use_container_width=True,
            key="v2_demo_exit",
        )
    st.divider()
    ui.markup('<div class="rail-label">SIMULATION</div>')
    replay = st.toggle(
        "Replay a saved run", key="v2_replay", on_change=stop_playback, disabled=ss.v2_demo_active
    )
    playback = replay or ss.v2_demo_active
    st.selectbox(
        "Scenario", list(PRESETS), key="v2_preset", on_change=new_engine, disabled=playback
    )
    st.selectbox(
        "Decision policy", list(POLICIES), key="v2_policy", on_change=new_engine, disabled=playback
    )
    if ss.v2_demo_active:
        st.caption(
            "Demo: School bus crash · seed 7 · offline scripted agents. "
            "Your simulation is preserved."
        )
    else:
        ui.markup(
            f'<div class="scenario-note">{html.escape(PRESETS[ss.v2_preset].description)}</div>'
        )
    with st.expander("Playback & configuration"):
        st.selectbox("Playback speed", list(PACE), key="v2_pace", disabled=playback)
        st.number_input(
            "Random seed", 0, 999, 7, key="v2_seed", on_change=new_engine, disabled=playback
        )
        st.number_input(
            "Town population",
            10_000,
            1_000_000,
            DEFAULT_POPULATION,
            step=10_000,
            key="v2_population",
            on_change=new_engine,
            disabled=playback,
        )
        st.toggle(
            "Review risky decisions",
            key="v2_human",
            on_change=new_engine,
            disabled=playback,
            help="Pause so a person can approve risky proposals.",
        )
        st.toggle("Auto-save completed runs", value=True, key="v2_autosave")
    replay_events = []
    if replay:
        from eval.run_report import SAVE_DIR

        logs = sorted(SAVE_DIR.glob("*/events.jsonl"), reverse=True)
        logs += sorted(settings.LOG_DIR.glob("run_*.jsonl"), reverse=True)
        if logs:
            choice = st.selectbox(
                "Saved run",
                logs,
                key="v2_saved_run",
                format_func=lambda p: p.parent.name if p.name == "events.jsonl" else p.name,
            )
            try:
                replay_events = read_jsonl(choice)
            except (ValueError, OSError) as exc:
                st.error(f"Could not read this run: {exc}")
        else:
            st.info("No saved runs yet. Save a scenario from Run report.")
    with st.expander("Map display"):
        layers = {name for name in LAYERS if st.toggle(name, value=True, key=f"v2_layer_{name}")}
    ui.markup(
        '<div class="rail-footer"><b>● Research simulation</b><p>Synthetic patients. '
        "A fictional town. Every action recorded.</p></div>"
    )

if ss.v2_present:
    st.markdown(
        f"<style>{Path(__file__).with_name('presentation.css').read_text()}</style>",
        unsafe_allow_html=True,
    )

title, start, advance, reset, help_col = st.columns(
    [3.2, 1.3, 1.15, 0.9, 0.65], vertical_alignment="center"
)
title.markdown(
    f'<div class="top-eyebrow">ORCA / COMMAND WORKSPACE</div><div class="top-title">{page}</div>',
    unsafe_allow_html=True,
)
start.button(
    "Pause simulation" if ss.v2_playing else "Start simulation",
    type="primary",
    use_container_width=True,
    on_click=toggle_play,
    disabled=playback,
)
advance.button(
    "Advance 15 min", use_container_width=True, on_click=step, args=(15,), disabled=playback
)
reset.button("Reset run", use_container_width=True, on_click=new_engine, disabled=playback)
with help_col.popover("Help", use_container_width=True):
    st.markdown("**Where to find everything**")
    for destination, description in PAGE_HELP.items():
        st.markdown(f"**{destination}** — {description}")
    st.divider()
    st.markdown("**Reading the dashboard**")
    st.markdown(
        "- **ER** means emergency department. Bars show occupied beds; numbers show free beds.\n"
        "- **Red / yellow / green / black** correspond to critical / serious / minor / "
        "expectant categories in the simulator.\n"
        "- **Reached care** includes patients who have already been discharged.\n"
        "- **Scripted agent** is an offline stand-in; **AI agent** identifies a model answer.\n"
        "- Changing scenario or policy resets the live run. Guided demo keeps it separate."
    )
    st.download_button(
        "Download demo & presenter guide",
        Path(__file__).with_name("DEMO_GUIDE.md").read_text(),
        file_name="ORCA-demo-guide.md",
        mime="text/markdown",
        key="v2_guide",
    )


def approval_cards() -> None:
    engine = ss.v2_engine
    if playback or engine.approval_mode != "interactive":
        return
    for proposal in engine.pending_approvals:
        if proposal.decided:
            continue
        action, alternative = proposal.action, proposal.alternative
        target = getattr(action, "hospital_id", None) or getattr(action, "incident_id", "")
        with st.container(border=True):
            st.warning(f"Review required · {action.unit_id} → {target}")
            for reason in proposal.reasons:
                st.write(reason)
            if getattr(action, "confidence", None) is not None:
                st.caption(f"Reported confidence: {action.confidence:.0%}")
            approve, change = st.columns(2)
            approve.button(
                "Approve proposal",
                key=f"v2_ok_{proposal.id}",
                type="primary",
                on_click=engine.decide_approval,
                args=(proposal.id, "approve"),
            )
            if alternative is not None:
                change.button(
                    f"Use hospital {alternative.hospital_id}",
                    key=f"v2_alt_{proposal.id}",
                    on_click=engine.decide_approval,
                    args=(proposal.id, "alternative"),
                )


def select_map_incident() -> None:
    selection = ss.get("v2_map", {}).get("selection", {}).get("points", [])
    for point in selection:
        incident_id = point.get("customdata")
        if isinstance(incident_id, list):
            incident_id = incident_id[0] if incident_id else None
        if isinstance(incident_id, str):
            ss.v2_focus = ss.v2_selected = incident_id
            break


def demo_controls() -> None:
    index = ss.v2_demo_index
    chapter = ss.v2_demo.chapters[index]
    total = len(ss.v2_demo.chapters)
    with st.container(border=True, key="v2_demo_panel"):
        ui.markup(
            f'<div class="demo-eyebrow">GUIDED DEMO · OFFLINE SCRIPTED AGENTS</div>'
            f'<div class="demo-title">{index + 1} / {total} &nbsp; '
            f"{html.escape(chapter.title)}</div>"
        )
        st.caption(chapter.look)
        notes, previous, following = st.columns([3, 1, 1], vertical_alignment="center")
        with notes.expander("Presenter notes · what to say"):
            st.write(chapter.say)
        previous.button(
            "Previous",
            on_click=demo_step,
            args=(-1,),
            disabled=index == 0,
            key="v2_demo_previous",
            use_container_width=True,
        )
        following.button(
            "Next step" if index < total - 1 else "Demo complete",
            on_click=demo_step,
            args=(1,),
            disabled=index == total - 1,
            type="primary",
            key="v2_demo_next",
            use_container_width=True,
        )
        st.progress((index + 1) / total)
        if page != chapter.page:
            st.button(
                f"Return to this step · {chapter.page}",
                on_click=demo_step,
                args=(0,),
                key="v2_demo_return",
            )


def render(events, tick: int, timings) -> None:
    visible = [e for e in events if e.tick <= tick]
    state = build_state(visible, upto=tick)
    town = TownProfile(population=state.run.get("population") or DEFAULT_POPULATION)
    k = state.kpis
    pending = (
        sum(not p.decided for p in ss.v2_engine.pending_approvals)
        if not playback and needs_review(ss.v2_engine)
        else 0
    )
    phase = (
        "Guided demo · paused"
        if ss.v2_demo_active
        else "Replay"
        if replay
        else "Review required"
        if pending
        else "Complete"
        if tick >= ss.v2_engine.end_tick
        else "Running"
        if ss.v2_playing
        else "Ready to run"
        if tick == 0
        else "Paused"
    )
    scenario_name = str(state.run.get("demand", ss.v2_preset)) if playback else ss.v2_preset
    ui.markup(
        f'<div class="command-status"><div><i></i><b>{phase}</b>'
        f"<span> / {html.escape(scenario_name)} · {town.population:,} residents</span></div>"
        f'<span class="clock">{wall_clock(tick)}<small>SIM TIME · +{tick} min</small>'
        "</span></div>"
    )
    if ss.v2_demo_active:
        source = "Offline scripted agents · demonstration"
    elif replay:
        models = sorted({d.get("model", "unknown") for d in state.agent_decisions})
        source = "Saved run · " + (
            ", ".join(models) if models else str(state.run.get("policy", "no agent calls yet"))
        )
    else:
        source = ss.v2_policy
    ui.markup(f'<div class="source-context"><b>Decision source</b> {html.escape(source)}</div>')
    if ss.v2_demo_active:
        demo_controls()
    elif tick == 0 and not replay:
        with st.container(border=True, key="v2_quickstart"):
            intro, action = st.columns([3, 1], vertical_alignment="center")
            intro.markdown(
                "**First time here? Follow a response in five steps.**  \n"
                "The guided demo pauses at each milestone and includes presenter notes."
            )
            if action.button(
                "Try guided demo",
                on_click=start_demo,
                use_container_width=True,
                key="v2_quick_demo",
            ):
                st.rerun(scope="app")
    approval_cards()
    issues = []
    if pending:
        issues.append(f"{pending} proposal(s) require your review")
    if k["waiting_at_er"]:
        issues.append(f"{k['waiting_at_er']} patient(s) waiting at an ER")
    if k["saturated"]:
        issues.append(f"{k['saturated']} hospital(s) at capacity")
    if issues:
        ui.markup(f'<div class="alert-note">{html.escape(" · ".join(issues))}</div>')
    options = ["All incidents", *sorted(state.incidents)]
    if ss.v2_selected not in options:
        ss.v2_selected = "All incidents"
    focus = None if ss.v2_selected == "All incidents" else ss.v2_selected

    if page == "Response overview":
        ui.overview_metrics(state)
        map_col, inspector_col = st.columns([2.5, 1], gap="medium")
        with map_col, st.container(border=True, key="v2_canvas"):
            ui.heading(
                "Response map", "Town coverage & active assignments", "SCHEMATIC · 20 × 20 KM"
            )
            fig = response_map(state, town, focus, layers)
            if ss.v2_present:
                fig.update_layout(height=510)
                for annotation in fig.layout.annotations:
                    annotation.font.size = max(12, annotation.font.size or 10)
            st.plotly_chart(
                fig,
                use_container_width=True,
                key="v2_map",
                on_select=select_map_incident,
                config={"displayModeBar": False, "scrollZoom": False},
            )
            ui.markup(
                '<div class="map-key"><span><i class="green"></i>Hospital</span>'
                '<span><i class="orange"></i>Incident</span>'
                '<span><i class="blue"></i>Ambulance</span>'
                '<span class="map-disclaimer">Assignment positions · not live GPS</span></div>'
            )
            ui.fleet_strip(state)
        with inspector_col, st.container(border=True, key="v2_desk"):
            ui.heading(
                "Incident desk",
                "Select a call or click its map marker",
                f"{k['active_calls']} OPEN",
            )
            incident_picker(state, collapsed=True)
            focus = None if ss.v2_focus == "All incidents" else ss.v2_focus
            ui.incident_inspector(state, focus)
        ui.heading(
            "Hospital capacity",
            "Emergency beds available across the network",
            f"{len(state.hospitals)} CONNECTED",
        )
        ui.hospital_grid(state)
        st.markdown("")
        ui.heading(
            "Response activity", "The latest actions, with their source", "MOST RECENT FIRST"
        )
        ui.activity(state, focus, limit=4)
        if st.button(
            "Open full decision trail",
            on_click=navigate,
            args=("Decision room",),
            key="v2_full_trail",
        ):
            st.rerun(scope="app")
        with st.expander("Incident register & ambulance assignments"):
            ui.incident_register(state)
            ui.fleet_board(state)
    elif page == "Hospital network":
        ui.heading("Care capacity", "Free beds, incoming patients, and hospital capabilities")
        ui.hospital_grid(state, detailed=True)
        st.markdown("")
        if st.button(
            "View ambulance assignments",
            on_click=navigate,
            args=("Ambulance fleet",),
            key="v2_go_fleet",
        ):
            st.rerun(scope="app")
        ui.heading("Patient distribution", "Patients delivered by hospital and triage")
        from app.state import transport_summary

        distribution = transport_summary(state)
        ui.table(
            ["Hospital", "Red", "Yellow", "Green", "Black"],
            [
                [hid, *[counts[c] for c in ("RED", "YELLOW", "GREEN", "BLACK")]]
                for hid, counts in sorted(distribution.items())
            ],
        )
    elif page == "Ambulance fleet":
        ui.heading("Ambulance fleet", "Find units, destinations, and current assignments")
        fleet_filter = st.radio(
            "Show units",
            ["All units", "Available", "Responding", "Standby"],
            horizontal=True,
            key="v2_fleet_filter",
        )
        ui.fleet_board(state, fleet_filter)
        st.caption(
            "Standby units are private resources activated through mutual aid. "
            "Returning units are not counted as available until they are idle."
        )
    elif page == "Decision room":
        ui.heading("How the response is coordinated", "Agent activity recorded in this run")
        ui.agent_pipeline(state)
        st.caption(
            f"{k['total_llm_calls']} agent calls · {k['total_negotiations']} proposals · "
            f"{k['fallbacks']} rule fallbacks · {k['escalations']} reviews raised."
            + (" Scripted agents are an offline stand-in, not a language model."
               if ss.v2_policy.startswith("Scripted") else "")
        )
        ui.heading("Decision trail", "Actual proposals, replies, and committed actions")
        incident_picker(state)
        focus = None if ss.v2_focus == "All incidents" else ss.v2_focus
        ui.activity(state, focus, limit=80)
        with st.expander("Agent call records"):
            ui.table(
                ["Time", "Agent", "Model", "Source", "Tokens"],
                [
                    [
                        d["wall"],
                        d["agent"],
                        d.get("model", ""),
                        "Scripted"
                        if d["source"] == "standin"
                        else "Cached"
                        if d.get("cache_hit")
                        else "Model call",
                        d.get("tokens", 0),
                    ]
                    for d in state.agent_decisions
                ],
            )
    else:
        ui.report(state)
        ui.heading("Keep this run", "Save a scorecard or download the event log for replay")
        save, download = st.columns([1, 2])
        if not playback:
            save.button("Save run & scorecard", on_click=save_current, key="v2_save")
        download.download_button(
            "Download event log",
            data="\n".join(e.model_dump_json() for e in visible) + "\n",
            file_name=f"orca-run-minute-{tick}.jsonl",
            mime="application/x-ndjson",
            key="v2_download",
        )
    ui.markup(
        '<div class="workspace-footer"><span>ORCA / Orchestrated Response and '
        "Capacity Allocation</span><span>Reproducible research · Synthetic patients · "
        "Simulated time</span></div>"
    )


if ss.v2_demo_active:
    chapter = ss.v2_demo.chapters[ss.v2_demo_index]
    render(ss.v2_demo.events, chapter.tick, [])
elif replay:
    if replay_events:
        end = max(e.tick for e in replay_events)
        # A log may contain only initialization at minute zero.
        tick = st.slider("Replay minute", 0, end, 0, key=f"v2_scrub_{choice}") if end else 0
        render(replay_events, tick, [])
    else:
        st.info("Choose a saved run in the sidebar, or turn replay off to run a scenario.")
else:

    @st.fragment(run_every=1.0 if ss.v2_playing else None)
    def live_view() -> None:
        # Links inside a fragment must refresh the outer navigation, controls, and theme too.
        if ss.v2_demo_active or page != ss.get("v2_page"):
            st.rerun(scope="app")
        engine = ss.v2_engine
        if ss.v2_playing:
            rate = PACE[ss.v2_pace]
            now = time.monotonic()
            ss.v2_budget = min(
                ss.get("v2_budget", 0.0) + (now - ss.get("v2_last_wall", now)) * rate,
                max(1, 3 * rate),
            )
            ss.v2_last_wall = now
            steps = int(ss.v2_budget)
            ss.v2_budget -= steps
            for _ in range(steps):
                if engine.tick >= engine.end_tick:
                    break
                if needs_review(engine):
                    ss.v2_playing = False
                    st.rerun(scope="app")
                engine.run(until=engine.tick + 1)
                if needs_review(engine):
                    ss.v2_playing = False
                    st.rerun(scope="app")
            if engine.tick >= engine.end_tick:
                ss.v2_playing = False
                st.rerun(scope="app")
        if engine.tick >= engine.end_tick and ss.get("v2_autosave", True):
            if ss.get("v2_autosaved_for") != id(engine):
                save_current(note=False)
                ss.v2_autosaved_for = id(engine)
        render(engine.log.events, engine.tick, engine.decision_timings)

    live_view()
