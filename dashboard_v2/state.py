"""V2 presentation data, derived from the shared event-log projection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.state import TRIAGE, FeedRow, transport_summary
from app.state import DashState as BaseState
from app.state import build_state as base_state
from sim.events import Event, EventType

__all__ = ["TRIAGE", "DashState", "FeedRow", "build_state", "transport_summary"]

NEG_TYPES = {"PROPOSE", "ACCEPT", "REJECT", "COUNTER", "RESOLVE", "ESCALATE"}


def wall_clock(tick: int) -> str:
    total = 14 * 60 + tick
    return f"{total // 60 % 24:02d}:{total % 60:02d}"


@dataclass
class DashState(BaseState):
    agent_decisions: list[dict[str, Any]] = field(default_factory=list)
    negotiations: list[dict[str, Any]] = field(default_factory=list)
    confidence_events: list[dict[str, Any]] = field(default_factory=list)
    fallbacks: list[dict[str, Any]] = field(default_factory=list)


def build_state(events: list[Event], upto: int | None = None) -> DashState:
    visible = [e for e in events if upto is None or e.tick <= upto]
    base = base_state(visible, upto)
    state = DashState(**vars(base))
    for call in base.ai_calls:
        messages = [
            r
            for r in base.feed
            if r.ai and r.ai.get("key") == call.get("key") and r.tick == call["tick"]
        ]
        state.agent_decisions.append(
            {
                **call,
                "wall": wall_clock(call["tick"]),
                "agent_kind": call["agent"].split(":")[0],
                "incident_id": next((r.incident_id for r in messages if r.incident_id), None),
                "explanation": " · ".join(dict.fromkeys(r.text for r in messages if r.text)),
                "source": "standin" if call.get("model") == "scripted" else "ai",
            }
        )
    for event in visible:
        p = event.payload
        common = {**p, "tick": event.tick, "wall": wall_clock(event.tick)}
        if event.type == EventType.MESSAGE and p.get("type") in NEG_TYPES:
            state.negotiations.append({**common, "msg_type": p["type"]})
        elif event.type in (EventType.ESCALATED, EventType.APPROVED, EventType.OVERRIDDEN):
            state.confidence_events.append({**common, "event_type": event.type.value})
        elif event.type == EventType.FALLBACK_USED:
            state.fallbacks.append(common)
    state.kpis.update(
        total_llm_calls=len(state.agent_decisions),
        total_tokens=sum(d.get("tokens", 0) for d in state.agent_decisions),
        total_negotiations=sum(n["msg_type"] == "PROPOSE" for n in state.negotiations),
        escalations=sum(c["event_type"] == "ESCALATED" for c in state.confidence_events),
        fallbacks=len(state.fallbacks),
    )
    return state
