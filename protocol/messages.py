"""Structured messages between agents, units, and hospitals (PLAN §14.1).

Every `MESSAGE` event in the log carries one of these as its payload, whether it comes from the
engine (pre-alerts, mutual aid, hospital status) or from an agent (proposals, counters). The
dashboard renders messages by this schema only.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(StrEnum):
    PRIORITY_REPORT = "PRIORITY_REPORT"
    PROPOSE = "PROPOSE"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    COUNTER = "COUNTER"
    ESCALATE = "ESCALATE"
    RESOLVE = "RESOLVE"
    STAFF_REQUEST = "STAFF_REQUEST"
    STAFF_RESPONSE = "STAFF_RESPONSE"
    PRE_ALERT = "PRE_ALERT"
    STATUS = "STATUS"
    MUTUAL_AID_REQUEST = "MUTUAL_AID_REQUEST"
    MUTUAL_AID_RESPONSE = "MUTUAL_AID_RESPONSE"


class Message(BaseModel):
    message_id: str
    tick: int
    state_version: int  # engine state version the sender used
    sender: str  # e.g. "dispatch", "hospital:B", "allocator", "AMB-3", "firm:MedRide"
    recipient: str  # agent id or "all"
    type: MessageType
    incident_id: str | None = None
    patient_ids: list[str] = Field(default_factory=list)
    proposed_action: dict[str, Any] | None = None
    reason: str = ""
    negotiation_round: int = 0
