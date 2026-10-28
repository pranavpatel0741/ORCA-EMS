"""Typed outputs of the four agent types (PLAN §14.2). Agents return these; never free text."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SeverityCounts(BaseModel):
    critical: int = 0
    serious: int = 0
    minor: int = 0
    expectant: int = 0


class PriorityReport(BaseModel):
    """Assessment agent: what this call is and how urgent."""

    incident_id: str
    mode: Literal["SINGLE", "MCI"]
    estimated: SeverityCounts
    needs_police: bool
    needs_fire: bool
    urgency: float = Field(ge=0.0, le=1.0)
    rationale: str


class Assignment(BaseModel):
    unit_id: str
    incident_id: str
    patient_ids: list[str] = Field(default_factory=list)  # empty: crew triages on arrival
    rationale: str


class RouteChoice(BaseModel):
    unit_id: str
    hospital_id: str
    rationale: str


class MutualAid(BaseModel):
    firm_id: str
    units: int


class DispatchPlan(BaseModel):
    """Dispatch agent: which units go where, and where loaded units take their patients."""

    assignments: list[Assignment] = Field(default_factory=list)
    routes: list[RouteChoice] = Field(default_factory=list)
    mutual_aid: MutualAid | None = None
    rationale: str


class AdmissionDecision(BaseModel):
    """Hospital agent: answer to a proposal addressed to this hospital."""

    hospital_id: str
    decision: Literal["ACCEPT", "REJECT", "COUNTER"]
    accepted_patient_ids: list[str] = Field(default_factory=list)
    counter_offer: str = ""  # e.g. "can take 1 of 2", "suggest Hospital C", "bay free in 20 min"
    suggested_hospital: str | None = None
    staff_request_nurses: int = 0  # nurses this hospital would need to accept more
    rationale: str


class StaffDecision(BaseModel):
    """Hospital agent: answer to another hospital's request for nurses."""

    hospital_id: str
    lend_nurses: int = Field(ge=0)
    rationale: str


class Resolution(BaseModel):
    """Allocator agent: settles conflicts and unresolved negotiations."""

    routes: list[RouteChoice] = Field(default_factory=list)
    assignments: list[Assignment] = Field(default_factory=list)
    unassigned_patient_ids: list[str] = Field(default_factory=list)
    escalate: bool = False
    rationale: str
