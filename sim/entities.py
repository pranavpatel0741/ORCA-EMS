"""Domain model (PLAN §6). Static configuration plus mutable state fields owned by the engine."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, PlainSerializer

Location = tuple[float, float]  # (lat, lon)


def _sorted_list(values: set) -> list:
    return sorted(values)


# Sets serialize in sorted order so scenario files and logs are byte-identical across runs.
SortedSet = PlainSerializer(_sorted_list, return_type=list, when_used="always")


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    SERIOUS = "SERIOUS"
    MINOR = "MINOR"
    EXPECTANT = "EXPECTANT"


class IncidentType(StrEnum):
    MEDICAL_CARDIAC = "MEDICAL_CARDIAC"
    MEDICAL_STROKE = "MEDICAL_STROKE"
    MEDICAL_GENERAL = "MEDICAL_GENERAL"
    FALL = "FALL"
    VEHICLE_CRASH = "VEHICLE_CRASH"
    BUS_CRASH = "BUS_CRASH"
    SHOOTING = "SHOOTING"


class Capability(StrEnum):
    TRAUMA_L1 = "TRAUMA_L1"
    TRAUMA_L2 = "TRAUMA_L2"
    CARDIAC_CATH = "CARDIAC_CATH"
    STROKE = "STROKE"
    GENERAL = "GENERAL"


class Owner(StrEnum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class UnitType(StrEnum):
    ALS = "ALS"
    BLS = "BLS"


class AmbulanceState(StrEnum):
    IDLE = "IDLE"
    EN_ROUTE = "EN_ROUTE"
    STAGING = "STAGING"
    ON_SCENE = "ON_SCENE"
    LOADING = "LOADING"
    TRANSPORTING = "TRANSPORTING"
    WAITING_AT_ER = "WAITING_AT_ER"
    HANDOVER = "HANDOVER"
    RETURNING = "RETURNING"


class PatientStatus(StrEnum):
    WAITING_ON_SCENE = "WAITING_ON_SCENE"
    IN_TRANSPORT = "IN_TRANSPORT"
    WAITING_AT_ER = "WAITING_AT_ER"
    IN_TREATMENT = "IN_TREATMENT"
    DISCHARGED = "DISCHARGED"
    DECEASED = "DECEASED"


class TeamKind(StrEnum):
    POLICE = "POLICE"
    FIRE = "FIRE"


class TeamState(StrEnum):
    IDLE = "IDLE"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    RETURNING = "RETURNING"


class Mode(StrEnum):
    SINGLE = "SINGLE"
    MCI = "MCI"


# --- Hospitals -------------------------------------------------------------------------------


class SurgeContract(BaseModel):
    max_surge_patients: int
    eligible_severities: Annotated[set[Severity], SortedSet]
    accepts_critical_trauma: bool


class Hospital(BaseModel):
    """Static hospital configuration. Live counters are held by `sim.hospital.HospitalState`."""

    id: str
    name: str
    location: Location
    owner: Owner
    capabilities: Annotated[set[Capability], SortedSet]
    er_beds_total: int
    trauma_bays_total: int
    ors_total: int
    trauma_surgeons_total: int
    nurses_total: int
    min_nurse_coverage: int
    stabilization_only: bool = False  # trauma bays usable only to stabilize (Hospital B)
    surge_contract: SurgeContract | None = None


# --- Units -----------------------------------------------------------------------------------


class Ambulance(BaseModel):
    id: str
    owner: Owner
    unit_type: UnitType
    home_station: Location
    location: Location
    state: AmbulanceState = AmbulanceState.IDLE
    state_until_tick: int | None = None
    firm_id: str | None = None
    assigned_incident: str | None = None
    onboard_patient_ids: list[str] = Field(default_factory=list)
    assigned_patient_ids: list[str] = Field(default_factory=list)
    destination_hospital: str | None = None

    MAX_CRITICAL: ClassVar[int] = 1
    MAX_NON_CRITICAL: ClassVar[int] = 2


class PrivateFirm(BaseModel):
    id: str
    name: str
    unit_ids: list[str]
    max_mutual_aid_units: int
    activation_minutes: int


class ResponderTeam(BaseModel):
    id: str
    kind: TeamKind
    home: Location
    location: Location
    state: TeamState = TeamState.IDLE
    state_until_tick: int | None = None
    assigned_incident: str | None = None


# --- Patients and incidents ------------------------------------------------------------------


class PatientNeeds(BaseModel):
    trauma_bay: bool = False
    trauma_surgeon: bool = False
    or_within_minutes: int | None = None
    er_bed: bool = True
    nurse: bool = True
    capability: Capability | None = None


class PatientTimestamps(BaseModel):
    call: int
    unit_on_scene: int | None = None
    loaded: int | None = None
    arrived_hospital: int | None = None
    definitive_care_start: int | None = None
    discharged: int | None = None
    deceased: int | None = None


class Patient(BaseModel):
    id: str
    incident_id: str
    true_severity: Severity  # hidden from agents
    observed_severity: Severity | None = None
    needs: PatientNeeds
    deterioration_rate: float = 0.0
    status: PatientStatus = PatientStatus.WAITING_ON_SCENE
    timestamps: PatientTimestamps
    walk_in: bool = False
    hospital_id: str | None = None
    ambulance_id: str | None = None
    survival_prob: float | None = None  # synthetic outcome model; frozen at definitive care


class Incident(BaseModel):
    id: str
    type: IncidentType
    location: Location
    call_tick: int
    reported_victims: int
    true_victim_ids: list[str]  # hidden from agents
    violent: bool = False
    scene_secured: bool = True
    scene_secured_tick: int | None = None  # hidden; set when police on scene + secure delay
    secure_delay_min: int = 10  # hidden; drawn by generator (5-15)
    needs_fire_extrication: bool = False
    extrication_min: int = 0  # hidden; minutes of fire work after fire arrives
    narrative: str = ""


# --- Scenario --------------------------------------------------------------------------------


class WalkIn(BaseModel):
    patient_id: str
    hospital_id: str
    tick: int


class Scenario(BaseModel):
    seed: int
    demand: str = "normal"  # normal | surge
    info: str = "complete"  # complete | partial
    horizon: int = 180  # minutes during which calls arrive
    drain_min: int = 120  # extra minutes simulated after the horizon
    hospitals: list[Hospital]
    initial_occupancy: dict[str, float] = Field(default_factory=dict)  # ER-bed fraction
    background_arrivals: bool = True
    ambulances: list[Ambulance]
    firms: list[PrivateFirm] = Field(default_factory=list)
    teams: list[ResponderTeam] = Field(default_factory=list)
    incidents: list[Incident]
    patients: list[Patient]
    walk_ins: list[WalkIn] = Field(default_factory=list)
