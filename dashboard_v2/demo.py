"""A reproducible, network-free presentation driven by real simulator events."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sim.engine import Engine
from sim.events import Event, EventType
from sim.presets import build_preset


@dataclass(frozen=True)
class Chapter:
    title: str
    page: str
    tick: int
    focus: str | None
    look: str
    say: str


@dataclass
class DemoRun:
    events: list[Event]
    chapters: list[Chapter]


def build_demo(cache_dir: Path) -> DemoRun:
    from orca_agents.llm_cache import LLMClient
    from orca_agents.orchestrator import AgentPolicy
    from orca_agents.scripted import ScriptedBackend

    engine = Engine(
        build_preset("School bus crash", seed=7),
        AgentPolicy(client=LLMClient(ScriptedBackend(), mode="live", cache_dir=cache_dir)),
    )
    engine.run()
    events = engine.log.events
    call = next(e for e in events if e.type == EventType.CALL_RECEIVED)
    proposal = next(
        e for e in events if e.type == EventType.MESSAGE and e.payload.get("type") == "PROPOSE"
    )
    care = next(
        e
        for e in events
        if e.type == EventType.PATIENT_STATE_CHANGED and e.payload.get("to") == "IN_TREATMENT"
    )
    focus = call.payload["incident_id"]
    return DemoRun(
        events,
        [
            Chapter(
                "Meet the town",
                "Response overview",
                0,
                None,
                "Point out the map, available ambulances, and hospital capacity below it.",
                "ORCA coordinates ambulances and hospitals in a synthetic emergency simulation. "
                "The question is where to send patients when capacity is limited.",
            ),
            Chapter(
                "Receive the emergency",
                "Response overview",
                call.tick,
                focus,
                "The incident desk shows the call, patient triage, and response milestones.",
                "A school bus crash puts pressure on the whole network. Each assignment and "
                "patient milestone is recorded, so we can follow the response.",
            ),
            Chapter(
                "Follow the negotiation",
                "Decision room",
                proposal.tick,
                focus,
                "Read a hospital proposal and reply in the decision trail; check the source label.",
                "The assessor, dispatcher, hospitals, and allocator have separate roles. "
                "This offline demo uses scripted stand-ins to show their coordination; "
                "these are not live language-model answers.",
            ),
            Chapter(
                "See patients reach care",
                "Hospital network",
                care.tick,
                focus,
                "Compare free beds, incoming patients, and the patient distribution table.",
                "The first patient has started treatment. Hospital capability and capacity "
                "matter alongside distance, and the engine validates every committed action.",
            ),
            Chapter(
                "Explain the outcomes",
                "Run report",
                engine.tick,
                focus,
                "Read treatment times together with the patients-in-care and deaths columns.",
                "The report shows what happened in this run, including delays and deaths. "
                "It does not establish that agents outperform a baseline; that needs "
                "controlled comparisons across identical scenarios.",
            ),
        ],
    )
