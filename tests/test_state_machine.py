import pytest

from sim.entities import (
    Ambulance,
    AmbulanceState,
    Incident,
    IncidentType,
    Owner,
    Patient,
    PatientNeeds,
    PatientStatus,
    PatientTimestamps,
    ResponderTeam,
    Severity,
    TeamKind,
    TeamState,
    UnitType,
)
from sim.events import EventLog, EventType, read_jsonl
from sim.state_machine import (
    AMBULANCE_TRANSITIONS,
    PATIENT_TRANSITIONS,
    TEAM_TRANSITIONS,
    IllegalTransition,
    can_reassign,
    secure_scene,
    transition_ambulance,
    transition_patient,
    transition_team,
)

LOC = (42.36, -71.06)


def make_amb(state: AmbulanceState = AmbulanceState.IDLE) -> Ambulance:
    return Ambulance(
        id="AMB-1", owner=Owner.PUBLIC, unit_type=UnitType.ALS,
        home_station=LOC, location=LOC, state=state,
    )


def make_patient(status: PatientStatus = PatientStatus.WAITING_ON_SCENE) -> Patient:
    return Patient(
        id="P-1", incident_id="I-1", true_severity=Severity.SERIOUS, needs=PatientNeeds(),
        status=status, timestamps=PatientTimestamps(call=0),
    )


def make_team(state: TeamState = TeamState.IDLE) -> ResponderTeam:
    return ResponderTeam(id="POL-1", kind=TeamKind.POLICE, home=LOC, location=LOC, state=state)


@pytest.mark.parametrize(
    "old,new", [(o, n) for o, ns in AMBULANCE_TRANSITIONS.items() for n in ns]
)
def test_ambulance_legal_transition_emits_one_event(old, new):
    amb, log = make_amb(old), EventLog("t")
    transition_ambulance(amb, new, 5, log, until=9)
    assert amb.state == new and amb.state_until_tick == 9
    assert len(log) == 1
    e = log.events[0]
    assert e.type == EventType.UNIT_STATE_CHANGED and e.tick == 5
    assert e.payload["from"] == old and e.payload["to"] == new


@pytest.mark.parametrize(
    "old,new",
    [(o, n) for o in AmbulanceState for n in AmbulanceState if n not in AMBULANCE_TRANSITIONS[o]],
)
def test_ambulance_illegal_transition_raises(old, new):
    amb, log = make_amb(old), EventLog("t")
    with pytest.raises(IllegalTransition):
        transition_ambulance(amb, new, 0, log)
    assert amb.state == old and len(log) == 0


@pytest.mark.parametrize("old,new", [(o, n) for o, ns in PATIENT_TRANSITIONS.items() for n in ns])
def test_patient_legal_transition_emits_one_event(old, new):
    p, log = make_patient(old), EventLog("t")
    transition_patient(p, new, 7, log)
    assert p.status == new and len(log) == 1
    assert log.events[0].type == EventType.PATIENT_STATE_CHANGED


@pytest.mark.parametrize(
    "old,new",
    [(o, n) for o in PatientStatus for n in PatientStatus if n not in PATIENT_TRANSITIONS[o]],
)
def test_patient_illegal_transition_raises(old, new):
    p, log = make_patient(old), EventLog("t")
    with pytest.raises(IllegalTransition):
        transition_patient(p, new, 0, log)
    assert len(log) == 0


def test_patient_timestamps_set_on_entry():
    p, log = make_patient(), EventLog("t")
    transition_patient(p, PatientStatus.IN_TRANSPORT, 10, log)
    transition_patient(p, PatientStatus.WAITING_AT_ER, 20, log)
    transition_patient(p, PatientStatus.IN_TREATMENT, 25, log)
    transition_patient(p, PatientStatus.DISCHARGED, 90, log)
    ts = p.timestamps
    assert (ts.loaded, ts.arrived_hospital, ts.definitive_care_start, ts.discharged) == (
        10, 20, 25, 90,
    )


@pytest.mark.parametrize("old,new", [(o, n) for o, ns in TEAM_TRANSITIONS.items() for n in ns])
def test_team_legal_transition_emits_one_event(old, new):
    team, log = make_team(old), EventLog("t")
    transition_team(team, new, 3, log)
    assert team.state == new and len(log) == 1
    assert log.events[0].payload["kind"] == TeamKind.POLICE


def test_team_illegal_transition_raises():
    team, log = make_team(TeamState.IDLE), EventLog("t")
    with pytest.raises(IllegalTransition):
        transition_team(team, TeamState.ON_SCENE, 0, log)


def test_secure_scene_once():
    inc = Incident(
        id="I-1", type=IncidentType.SHOOTING, location=LOC, call_tick=0, reported_victims=2,
        true_victim_ids=["P-1"], violent=True, scene_secured=False,
    )
    log = EventLog("t")
    secure_scene(inc, 12, log)
    assert inc.scene_secured and log.events[0].type == EventType.SCENE_SECURED
    with pytest.raises(IllegalTransition):
        secure_scene(inc, 13, log)


@pytest.mark.parametrize(
    "state,expected",
    [
        (AmbulanceState.IDLE, True),
        (AmbulanceState.RETURNING, True),
        (AmbulanceState.EN_ROUTE, True),
        (AmbulanceState.STAGING, True),
        (AmbulanceState.ON_SCENE, False),
        (AmbulanceState.LOADING, False),
        (AmbulanceState.TRANSPORTING, False),
        (AmbulanceState.WAITING_AT_ER, False),
        (AmbulanceState.HANDOVER, False),
    ],
)
def test_can_reassign_by_state(state, expected):
    assert can_reassign(make_amb(state)) is expected


def test_loaded_ambulance_cannot_be_reassigned():
    amb = make_amb(AmbulanceState.EN_ROUTE)
    amb.onboard_patient_ids = ["P-1"]
    assert not can_reassign(amb)


def test_event_log_jsonl_roundtrip(tmp_path):
    amb, log = make_amb(), EventLog("run1")
    transition_ambulance(amb, AmbulanceState.EN_ROUTE, 1, log, until=6, incident_id="I-1")
    path = log.write_jsonl(tmp_path / "run.jsonl")
    events = read_jsonl(path)
    assert events == log.events
