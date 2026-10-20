"""Proposed actions. Policies and agents emit these; only `Engine.commit` applies them."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Dispatch(BaseModel):
    """Send a unit to an incident, optionally for specific patients and a target hospital."""

    kind: Literal["dispatch"] = "dispatch"
    unit_id: str
    incident_id: str
    patient_ids: list[str] = Field(default_factory=list)
    target_hospital: str | None = None
    rationale: str = ""


class RouteToHospital(BaseModel):
    """Set the destination hospital for a unit that is on scene or loading."""

    kind: Literal["route"] = "route"
    unit_id: str
    hospital_id: str
    rationale: str = ""


class LendStaff(BaseModel):
    kind: Literal["lend_staff"] = "lend_staff"
    lender_id: str
    borrower_id: str
    nurses: int
    rationale: str = ""


Action = Dispatch | RouteToHospital | LendStaff
