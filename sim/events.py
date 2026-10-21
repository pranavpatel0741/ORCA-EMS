"""Event types and the JSONL event log (PLAN §13)."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    RUN_STARTED = "RUN_STARTED"  # scenario summary incl. patient list (for log-only metrics)
    CALL_RECEIVED = "CALL_RECEIVED"
    SCENE_REPORT = "SCENE_REPORT"
    SCENE_SECURED = "SCENE_SECURED"
    PRIORITY_REPORT = "PRIORITY_REPORT"
    MESSAGE = "MESSAGE"
    PROPOSAL_VALIDATED = "PROPOSAL_VALIDATED"
    PROPOSAL_REJECTED = "PROPOSAL_REJECTED"
    ESCALATED = "ESCALATED"
    APPROVED = "APPROVED"
    OVERRIDDEN = "OVERRIDDEN"
    FALLBACK_USED = "FALLBACK_USED"
    COMMITTED = "COMMITTED"
    UNIT_STATE_CHANGED = "UNIT_STATE_CHANGED"
    PATIENT_STATE_CHANGED = "PATIENT_STATE_CHANGED"
    HOSPITAL_STATUS = "HOSPITAL_STATUS"
    WALK_IN = "WALK_IN"
    STAFF_LOAN = "STAFF_LOAN"
    MONITOR_ALERT = "MONITOR_ALERT"
    LLM_CALL = "LLM_CALL"
    RUN_SUMMARY = "RUN_SUMMARY"


class Event(BaseModel):
    run_id: str
    tick: int
    type: EventType
    actor: str
    payload: dict[str, Any] = Field(default_factory=dict)


class EventLog:
    """Append-only, in-memory event log with JSONL export.

    Payloads must be JSON-serializable and deterministic. Wall-clock data (e.g. LLM latency)
    is only allowed inside `LLM_CALL` payloads, which reproducibility checks exclude.
    """

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.events: list[Event] = []

    def emit(
        self, tick: int, type: EventType, actor: str, payload: dict[str, Any] | None = None
    ) -> Event:
        event = Event(run_id=self.run_id, tick=tick, type=type, actor=actor, payload=payload or {})
        self.events.append(event)
        return event

    def of_type(self, *types: EventType) -> list[Event]:
        return [e for e in self.events if e.type in types]

    def __len__(self) -> int:
        return len(self.events)

    def write_jsonl(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            for e in self.events:
                f.write(json.dumps(e.model_dump(mode="json"), sort_keys=True) + "\n")
        return path


def read_jsonl(path: str | Path) -> list[Event]:
    with Path(path).open() as f:
        return [Event.model_validate_json(line) for line in f if line.strip()]
