"""Explicit state machines for ambulances, patients, scenes, and responder teams (PLAN §7).

Every successful transition emits exactly one event. Illegal transitions raise.
"""

from __future__ import annotations

from typing import Any

from sim.entities import (
    Ambulance,
    AmbulanceState,
    Incident,
    Patient,
    PatientStatus,
    ResponderTeam,
    TeamState,
)
from sim.events import EventLog, EventType

A = AmbulanceState
P = PatientStatus
T = TeamState

AMBULANCE_TRANSITIONS: dict[AmbulanceState, set[AmbulanceState]] = {
    A.IDLE: {A.EN_ROUTE},
    # EN_ROUTE -> EN_ROUTE is an (empty) reassignment to a different incident.
    A.EN_ROUTE: {A.EN_ROUTE, A.STAGING, A.ON_SCENE, A.RETURNING},
    # Staging releases into a short EN_ROUTE leg to the scene once it is secured.
    A.STAGING: {A.EN_ROUTE, A.RETURNING},
    A.ON_SCENE: {A.LOADING, A.RETURNING},
    A.LOADING: {A.TRANSPORTING},
    A.TRANSPORTING: {A.WAITING_AT_ER},
    A.WAITING_AT_ER: {A.HANDOVER},
    A.HANDOVER: {A.RETURNING},
    A.RETURNING: {A.IDLE, A.EN_ROUTE},
}

PATIENT_TERMINAL = {P.DISCHARGED, P.DECEASED}
PATIENT_TRANSITIONS: dict[PatientStatus, set[PatientStatus]] = {
    # WAITING_ON_SCENE -> WAITING_AT_ER covers walk-ins (self-transport).
    P.WAITING_ON_SCENE: {P.IN_TRANSPORT, P.WAITING_AT_ER, P.DECEASED},
    P.IN_TRANSPORT: {P.WAITING_AT_ER, P.DECEASED},
    P.WAITING_AT_ER: {P.IN_TREATMENT, P.DECEASED},
    P.IN_TREATMENT: {P.DISCHARGED, P.DECEASED},
    P.DISCHARGED: set(),
    P.DECEASED: set(),
}

TEAM_TRANSITIONS: dict[TeamState, set[TeamState]] = {
    T.IDLE: {T.EN_ROUTE},
    T.EN_ROUTE: {T.ON_SCENE, T.RETURNING},
    T.ON_SCENE: {T.RETURNING},
    T.RETURNING: {T.IDLE, T.EN_ROUTE},
}

# Patient timestamp set on entering a status.
_PATIENT_TIMESTAMP = {
    P.IN_TRANSPORT: "loaded",
    P.WAITING_AT_ER: "arrived_hospital",
    P.IN_TREATMENT: "definitive_care_start",
    P.DISCHARGED: "discharged",
    P.DECEASED: "deceased",
}

REASSIGNABLE = {A.IDLE, A.RETURNING, A.EN_ROUTE, A.STAGING}


class IllegalTransition(Exception):
    pass


def transition_ambulance(
    amb: Ambulance,
    new: AmbulanceState,
    tick: int,
    log: EventLog,
    *,
    until: int | None = None,
    actor: str = "engine",
    **payload: Any,
) -> None:
    old = amb.state
    if new not in AMBULANCE_TRANSITIONS[old]:
        raise IllegalTransition(f"{amb.id}: {old} -> {new}")
    amb.state = new
    amb.state_until_tick = until
    log.emit(
        tick,
        EventType.UNIT_STATE_CHANGED,
        actor,
        {"unit_id": amb.id, "kind": "AMBULANCE", "from": old, "to": new, "until": until,
         **payload},
    )


def transition_patient(
    patient: Patient,
    new: PatientStatus,
    tick: int,
    log: EventLog,
    *,
    actor: str = "engine",
    **payload: Any,
) -> None:
    old = patient.status
    if new not in PATIENT_TRANSITIONS[old]:
        raise IllegalTransition(f"{patient.id}: {old} -> {new}")
    patient.status = new
    field = _PATIENT_TIMESTAMP.get(new)
    if field is not None:
        setattr(patient.timestamps, field, tick)
    log.emit(
        tick,
        EventType.PATIENT_STATE_CHANGED,
        actor,
        {"patient_id": patient.id, "from": old, "to": new, **payload},
    )


def transition_team(
    team: ResponderTeam,
    new: TeamState,
    tick: int,
    log: EventLog,
    *,
    until: int | None = None,
    actor: str = "engine",
    **payload: Any,
) -> None:
    old = team.state
    if new not in TEAM_TRANSITIONS[old]:
        raise IllegalTransition(f"{team.id}: {old} -> {new}")
    team.state = new
    team.state_until_tick = until
    log.emit(
        tick,
        EventType.UNIT_STATE_CHANGED,
        actor,
        {"unit_id": team.id, "kind": team.kind, "from": old, "to": new, "until": until,
         **payload},
    )


def secure_scene(incident: Incident, tick: int, log: EventLog, *, actor: str = "engine") -> None:
    """UNSECURED -> SECURED. Only valid once, and only for violent incidents."""
    if incident.scene_secured:
        raise IllegalTransition(f"{incident.id}: scene already secured")
    incident.scene_secured = True
    log.emit(tick, EventType.SCENE_SECURED, actor, {"incident_id": incident.id})


def can_reassign(amb: Ambulance) -> bool:
    """A unit may be reassigned while IDLE, RETURNING, or EN_ROUTE/STAGING and empty."""
    return amb.state in REASSIGNABLE and not amb.onboard_patient_ids
