"""What decision makers are allowed to see (PLAN §11).

Policies (baselines and agents alike) receive an `Observation` built by the engine each tick.
It is a frozen copy: changing it cannot change the world. Hidden truth (true severity before a
scene report, true victim counts, live capacity in the partial setting) never appears here.

- Hospital board: live (complete) / refreshed every 15 min, stale in between (partial).
- Victims and severity: known after the call (complete) / only the caller's estimate until the
  first unit's scene report (partial).
- Ambulance status and position, scene secured: true in both settings.
- Walk-ins: known on arrival (complete) / known at the next board update (partial).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from sim.entities import Capability, Location, PatientNeeds, Severity
from sim.travel import TimingConfig, estimate_eta

Info = Literal["complete", "partial"]


class ObsPatient(BaseModel):
    id: str
    incident_id: str
    severity: Severity | None  # observed severity (None until assessed)
    needs: PatientNeeds | None
    status: str
    ambulance_id: str | None = None


class ObsIncident(BaseModel):
    id: str
    type: str
    location: Location
    call_tick: int
    reported_victims: int
    narrative: str
    violent: bool
    secured: bool
    needs_fire: bool
    scene_reported: bool  # a unit has reported from the scene
    patients: list[ObsPatient] = Field(default_factory=list)  # empty until known


class ObsUnit(BaseModel):
    id: str
    owner: str
    unit_type: str
    state: str
    location: Location
    home: Location
    available: bool  # in service (private units only after mutual-aid activation)
    reassignable: bool
    assigned_incident: str | None
    patient_ids: list[str]
    destination: str | None


class ObsHospital(BaseModel):
    id: str
    name: str
    location: Location
    owner: str
    capabilities: list[Capability]
    stabilization_only: bool
    contract: dict[str, Any] | None
    totals: dict[str, int]  # structural capacity (static)
    free: dict[str, int]  # from the status board
    er_occupancy: float
    queue: int
    boarding: int
    board_tick: int  # when the board was last updated


class ObsFirm(BaseModel):
    id: str
    unit_ids: list[str]
    max_units: int
    activation_minutes: int
    in_use: int  # active or pending


class Rejection(BaseModel):
    tick: int
    action: dict[str, Any]
    rule_id: str
    code: str  # reason code only; full reasons may contain hidden truth


class Observation(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    tick: int
    state_version: int
    info: Info
    timing: TimingConfig
    incidents: dict[str, ObsIncident]
    units: dict[str, ObsUnit]
    hospitals: dict[str, ObsHospital]
    firms: dict[str, ObsFirm]
    rejections: list[Rejection] = Field(default_factory=list)
    surge_active: bool = False
    # Policies may append protocol messages / LLM usage here; the engine logs them.
    outbox: list[dict[str, Any]] = Field(default_factory=list)
    llm_calls: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)  # e.g. ESCALATED, FALLBACK_USED

    # --- helpers shared by baselines and agents (same ETA model, PLAN §9) ----------------------

    def eta(self, a: Location, b: Location) -> float:
        return estimate_eta(a, b, self.timing)["median_min"]

    def eta_p90(self, a: Location, b: Location) -> float:
        return estimate_eta(a, b, self.timing)["p90_min"]

    def waiting(self, incident_id: str) -> list[ObsPatient]:
        """Known patients still waiting on scene with no unit assigned."""
        return [p for p in self.incidents[incident_id].patients
                if p.status == "WAITING_ON_SCENE" and p.ambulance_id is None]

    def unassigned_victims(self, incident_id: str) -> int:
        """Victims still needing a unit: known patients, or the reported estimate before the
        scene report minus units already sent."""
        inc = self.incidents[incident_id]
        if inc.scene_reported or inc.patients:
            return len(self.waiting(incident_id))
        sent = sum(1 for u in self.units.values() if u.assigned_incident == incident_id)
        return max(0, inc.reported_victims - 2 * sent)

    def free_units(self) -> list[ObsUnit]:
        return [u for u in self.units.values()
                if u.available and u.state in ("IDLE", "RETURNING") and u.reassignable]

    def units_needing_destination(self) -> list[ObsUnit]:
        return [u for u in self.units.values()
                if u.state in ("ON_SCENE", "LOADING") and u.patient_ids and u.destination is None]

    def patient(self, pid: str) -> ObsPatient | None:
        for inc in self.incidents.values():
            for p in inc.patients:
                if p.id == pid:
                    return p
        return None

    def incoming(self, hospital_id: str) -> list[ObsPatient]:
        """Patients this dispatcher has already sent toward `hospital_id` (its own knowledge)."""
        out = []
        for u in self.units.values():
            if u.destination == hospital_id and u.state in ("ON_SCENE", "LOADING",
                                                            "TRANSPORTING"):
                out += [p for pid in u.patient_ids if (p := self.patient(pid))]
        return out

    def send(self, sender: str, recipient: str, type: str, reason: str, **fields: Any) -> None:
        self.outbox.append({"sender": sender, "recipient": recipient, "type": type,
                            "reason": reason, **fields})
