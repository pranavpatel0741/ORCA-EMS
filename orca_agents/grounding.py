"""Validate model references against observed input before orchestration uses an answer.

This checks structured facts and identity, not the truth of free-text rationales. The engine's
validator remains responsible for action legality and capacity at commit time.
"""

from __future__ import annotations

from orca_agents.models import (
    AdmissionDecision,
    DispatchPlan,
    PriorityReport,
    Resolution,
    StaffDecision,
)
from sim.observations import Observation


def validate_output(output, payload: dict, obs: Observation) -> None:
    def require(condition: bool, reason: str) -> None:
        if not condition:
            raise ValueError(f"ungrounded output: {reason}")

    def patients(ids: list[str], incident_id: str | None = None) -> None:
        require(len(ids) == len(set(ids)), "duplicate patient IDs")
        for pid in ids:
            patient = obs.patient(pid)
            require(patient is not None, f"patient {pid} was not observed")
            if incident_id:
                require(
                    patient.incident_id == incident_id, f"patient {pid} belongs to another call"
                )

    def assignments(rows, scope: set[str] | None = None) -> None:
        for row in rows:
            require(row.unit_id in obs.units, f"unknown ambulance {row.unit_id}")
            require(scope is None or row.unit_id in scope, "allocator assigned an unrelated unit")
            require(row.incident_id in obs.incidents, f"unknown call {row.incident_id}")
            patients(row.patient_ids, row.incident_id)

    def routes(rows, scope: set[str] | None = None) -> None:
        for row in rows:
            require(row.unit_id in obs.units, f"unknown ambulance {row.unit_id}")
            require(scope is None or row.unit_id in scope, "allocator routed an unrelated unit")
            require(row.hospital_id in obs.hospitals, f"unknown hospital {row.hospital_id}")

    if isinstance(output, PriorityReport):
        require(output.incident_id == payload["call"]["id"], "assessment names another call")
        if payload.get("scene_report") is not None:
            actual = payload["scene_report"]
            require(
                all(
                    count == actual.get(severity, 0)
                    for severity, count in output.estimated.model_dump().items()
                ),
                "assessment contradicts the observed scene counts",
            )
    elif isinstance(output, AdmissionDecision):
        require(output.hospital_id == payload["hospital"], "hospital answer has the wrong identity")
        proposed = {p["id"] for proposal in payload["proposals"] for p in proposal["patients"]}
        accepted = output.accepted_patient_ids
        require(len(accepted) == len(set(accepted)), "duplicate accepted patient IDs")
        require(set(accepted) <= proposed, "hospital accepted patients not in the proposal")
        require(output.decision != "REJECT" or not accepted, "rejection also accepts patients")
        require(
            output.decision != "ACCEPT" or not accepted or set(accepted) == proposed,
            "ACCEPT lists only part of the proposed load; use COUNTER",
        )
        require(
            output.suggested_hospital is None or output.suggested_hospital in obs.hospitals,
            "suggested hospital does not exist",
        )
    elif isinstance(output, StaffDecision):
        require(output.hospital_id == payload["hospital"], "staff answer has the wrong identity")
        require(output.lend_nurses <= payload["request"]["nurses"], "staff loan exceeds request")
    elif isinstance(output, DispatchPlan):
        assignments(output.assignments)
        routes(output.routes)
        if output.mutual_aid:
            require(output.mutual_aid.firm_id in obs.firms, "unknown mutual-aid firm")
    elif isinstance(output, Resolution):
        scope = {unit["id"] for unit in payload["units"]}
        assignments(output.assignments, scope)
        routes(output.routes, scope)
        patients(output.unassigned_patient_ids)
