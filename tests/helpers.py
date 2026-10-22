"""Test fixtures: hand-built scenarios and a simple greedy test policy."""

from __future__ import annotations

from baselines.nearest import NearestPolicy
from sim.entities import (
    Ambulance,
    Capability,
    Hospital,
    Incident,
    IncidentType,
    Owner,
    Patient,
    PatientNeeds,
    PatientStatus,
    PatientTimestamps,
    ResponderTeam,
    Scenario,
    Severity,
    TeamKind,
    UnitType,
)

HOSP_LOC = (42.36, -71.06)
STATION = (42.31, -71.06)
SCENE = (42.41, -71.06)

SERIOUS_NEEDS = PatientNeeds(er_bed=True, nurse=True, capability=Capability.GENERAL)
CRITICAL_TRAUMA_NEEDS = PatientNeeds(
    trauma_bay=True, trauma_surgeon=True, or_within_minutes=60, er_bed=False, nurse=True,
    capability=Capability.TRAUMA_L1,
)
MINOR_NEEDS = PatientNeeds(er_bed=True, nurse=True, capability=Capability.GENERAL)


def hospital(hid: str = "H", loc=HOSP_LOC, **kw) -> Hospital:
    base = dict(
        id=hid, name=f"Hospital {hid}", location=loc, owner=Owner.PUBLIC,
        capabilities={Capability.TRAUMA_L1, Capability.GENERAL}, er_beds_total=10,
        trauma_bays_total=2, ors_total=2, trauma_surgeons_total=2, nurses_total=8,
        min_nurse_coverage=4,
    )
    base.update(kw)
    return Hospital(**base)


def ambulance(aid: str = "AMB-1", home=STATION, **kw) -> Ambulance:
    return Ambulance(id=aid, owner=Owner.PUBLIC, unit_type=UnitType.ALS, home_station=home,
                     location=home, **kw)


def patient(pid: str, inc: str, sev: Severity, needs: PatientNeeds, call: int) -> Patient:
    return Patient(id=pid, incident_id=inc, true_severity=sev, needs=needs,
                   timestamps=PatientTimestamps(call=call))


def mini_scenario() -> Scenario:
    """1 hospital, 1 ambulance, 1 call with one SERIOUS patient at tick 2. No background load."""
    return Scenario(
        seed=0, horizon=120, drain_min=0, background_arrivals=False,
        hospitals=[hospital()], ambulances=[ambulance()],
        incidents=[Incident(id="I-1", type=IncidentType.MEDICAL_GENERAL, location=SCENE,
                            call_tick=2, reported_victims=1, true_victim_ids=["P-1"])],
        patients=[patient("P-1", "I-1", Severity.SERIOUS, SERIOUS_NEEDS, 2)],
    )


def stress_scenario(seed: int = 3) -> Scenario:
    """Several incidents incl. a violent scene and an extrication, 2 hospitals, background load."""
    hospitals = [
        hospital("A"),
        hospital("B", loc=(42.35, -71.10), capabilities={Capability.GENERAL},
                 trauma_bays_total=0, ors_total=0, trauma_surgeons_total=0, er_beds_total=6,
                 nurses_total=5, min_nurse_coverage=3),
    ]
    ambs = [ambulance(f"AMB-{i}", home=h) for i, h in
            enumerate([STATION, HOSP_LOC, (42.34, -71.09), STATION], start=1)]
    teams = [
        ResponderTeam(id="POL-1", kind=TeamKind.POLICE, home=(42.37, -71.05),
                      location=(42.37, -71.05)),
        ResponderTeam(id="FIRE-1", kind=TeamKind.FIRE, home=STATION, location=STATION),
    ]
    incidents, patients = [], []
    specs = [
        ("I-1", IncidentType.MEDICAL_CARDIAC, (42.38, -71.07), 1, [Severity.SERIOUS], {}),
        ("I-2", IncidentType.SHOOTING, (42.40, -71.04), 5,
         [Severity.CRITICAL, Severity.SERIOUS], {"violent": True, "scene_secured": False,
                                                 "secure_delay_min": 8}),
        ("I-3", IncidentType.VEHICLE_CRASH, (42.33, -71.08), 12,
         [Severity.CRITICAL, Severity.MINOR, Severity.MINOR],
         {"needs_fire_extrication": True, "extrication_min": 12}),
        ("I-4", IncidentType.FALL, (42.36, -71.11), 20, [Severity.MINOR], {}),
        ("I-5", IncidentType.BUS_CRASH, (42.355, -71.065), 30,
         [Severity.CRITICAL, Severity.SERIOUS, Severity.SERIOUS, Severity.MINOR, Severity.MINOR,
          Severity.MINOR], {}),
    ]
    for iid, itype, loc, call, sevs, extra in specs:
        pids = []
        for k, sev in enumerate(sevs):
            pid = f"{iid}-P{k}"
            needs = {Severity.CRITICAL: CRITICAL_TRAUMA_NEEDS, Severity.SERIOUS: SERIOUS_NEEDS}.get(
                sev, MINOR_NEEDS)
            patients.append(patient(pid, iid, sev, needs, call))
            pids.append(pid)
        incidents.append(Incident(id=iid, type=itype, location=loc, call_tick=call,
                                  reported_victims=len(pids), true_victim_ids=pids, **extra))
    return Scenario(seed=seed, horizon=90, drain_min=150, hospitals=hospitals,
                    initial_occupancy={"A": 0.6, "B": 0.7}, ambulances=ambs, teams=teams,
                    incidents=incidents, patients=patients)


class GreedyTestPolicy(NearestPolicy):
    """Nearest free unit per waiting patient group; nearest hospital the validator accepts."""

    name = "greedy_test"


def patient_done(p: Patient) -> bool:
    return p.status in (PatientStatus.IN_TREATMENT, PatientStatus.DISCHARGED,
                        PatientStatus.DECEASED)
