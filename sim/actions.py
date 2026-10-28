"""Proposed actions. Policies and agents emit these; only `Engine.commit` applies them.

Actions are frozen and forbid extra fields (part of R9: agents can only request these changes).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Action(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Dispatch(_Action):
    """Send a unit to an incident, optionally for specific patients and a target hospital."""

    kind: Literal["dispatch"] = "dispatch"
    unit_id: str
    incident_id: str
    patient_ids: list[str] = Field(default_factory=list)
    target_hospital: str | None = None
    rationale: str = ""
    confidence: float | None = None  # set by the agents' confidence gate (PLAN §14.5)
    needs_review: bool = False  # the proposer asks for human review


class RouteToHospital(_Action):
    """Set the destination hospital for a unit that is on scene or loading."""

    kind: Literal["route"] = "route"
    unit_id: str
    hospital_id: str
    rationale: str = ""
    confidence: float | None = None
    needs_review: bool = False


class LendStaff(_Action):
    kind: Literal["lend_staff"] = "lend_staff"
    lender_id: str
    borrower_id: str
    nurses: int
    rationale: str = ""


class ActivateMutualAid(_Action):
    """Ask a private firm to activate `units` ambulances under its mutual-aid contract."""

    kind: Literal["mutual_aid"] = "mutual_aid"
    firm_id: str
    units: int
    rationale: str = ""


Action = Dispatch | RouteToHospital | LendStaff | ActivateMutualAid
ACTION_TYPES = (Dispatch, RouteToHospital, LendStaff, ActivateMutualAid)
