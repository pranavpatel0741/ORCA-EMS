"""R1–R9: one passing and one failing case per rule (PLAN §19)."""

import pytest

from sim.actions import ActivateMutualAid, Dispatch, LendStaff, RouteToHospital
from sim.engine import Engine
from sim.entities import AmbulanceState, Severity
from sim.generator import generate
from sim.validator import (
    r1_unit_assignable,
    r2_hospital_resources,
    r3_critical_trauma,
    r4_private_contracts,
    r5_scene_safety,
    r6_human_review,
    r7_ambulance_capacity,
    r8_staff_loans,
    r9_known_action,
    scene_entry_allowed,
)


@pytest.fixture
def surge():
    """Seed 7 surge at tick 36: shooting (MCI-1) and bus crash (MCI-2) both active."""
    engine = Engine(generate(7, "surge"), None)
    engine.run(until=36)
    return engine


def idle_unit(engine):
    return next(a.id for a in sorted(engine.ambulances.values(), key=lambda a: a.id)
                if a.state == AmbulanceState.IDLE and engine.unit_available(a.id))


def bus_patients(engine, sev, trauma=None):
    out = [p for p in engine.patients.values() if p.incident_id == "MCI-2"
           and p.true_severity == sev]
    if trauma is not None:
        out = [p for p in out if p.needs.trauma_bay == trauma]
    return sorted(out, key=lambda p: p.id)


def saturate_trauma(engine, hid):
    """Occupy every trauma bay and surgeon at `hid` for a long time."""
    hs = engine.hospitals[hid]
    hs.occupied["trauma_bay"] = hs.total("trauma_bay")
    hs.occupied["surgeon"] = hs.total("surgeon")
    from sim.hospital import Treatment
    hs.treatments.append(Treatment(id=f"X-{hid}", severity=Severity.CRITICAL,
                                   held={"trauma_bay": hs.total("trauma_bay"),
                                         "surgeon": hs.total("surgeon")},
                                   phase="er", end_tick=10_000, background=True))


# --- R1 ----------------------------------------------------------------------------------------

def test_r1_pass_and_fail(surge):
    unit = idle_unit(surge)
    pid = bus_patients(surge, Severity.SERIOUS)[0].id
    assert r1_unit_assignable(Dispatch(unit_id=unit, incident_id="MCI-2", patient_ids=[pid]),
                              surge).ok
    dup = r1_unit_assignable(Dispatch(unit_id=unit, incident_id="MCI-2",
                                      patient_ids=[pid, pid]), surge)
    assert not dup.ok and dup.code == "DUPLICATE_PATIENT"
    inactive = r1_unit_assignable(Dispatch(unit_id="PVT-1", incident_id="MCI-2"), surge)
    assert not inactive.ok and inactive.code == "NOT_ACTIVATED"


# --- R2 ----------------------------------------------------------------------------------------

def test_r2_pass_and_fail(surge):
    unit = idle_unit(surge)
    pid = bus_patients(surge, Severity.SERIOUS)[0].id
    assert r2_hospital_resources(Dispatch(unit_id=unit, incident_id="MCI-2", patient_ids=[pid],
                                          target_hospital="A"), surge).ok
    empty = r2_hospital_resources(Dispatch(unit_id=unit, incident_id="MCI-2",
                                           target_hospital="A"), surge)
    assert not empty.ok and empty.code == "TARGET_WITHOUT_PATIENTS"


# --- R3 ----------------------------------------------------------------------------------------

def test_r3_fail_stabilization_bay_when_trauma_center_reachable(surge):
    unit = idle_unit(surge)
    crit = bus_patients(surge, Severity.CRITICAL, trauma=True)[0]
    res = r3_critical_trauma(Dispatch(unit_id=unit, incident_id="MCI-2", patient_ids=[crit.id],
                                      target_hospital="B"), surge)
    assert not res.ok and res.code in ("TRAUMA_CENTER_REACHABLE",
                                       "STABILIZATION_NOT_MOST_UNSTABLE")
    to_d = r3_critical_trauma(Dispatch(unit_id=unit, incident_id="MCI-2", patient_ids=[crit.id],
                                       target_hospital="D"), surge)
    assert not to_d.ok and to_d.code == "NOT_TRAUMA_CENTER"


def test_r3_pass_stabilization_bay_for_most_unstable_when_centers_saturated(surge):
    saturate_trauma(surge, "A")
    saturate_trauma(surge, "C")
    unit = idle_unit(surge)
    crits = bus_patients(surge, Severity.CRITICAL, trauma=True)
    most_unstable = min(crits, key=lambda p: (p.survival_prob or 1.0, p.id))
    res = r3_critical_trauma(Dispatch(unit_id=unit, incident_id="MCI-2",
                                      patient_ids=[most_unstable.id], target_hospital="B"), surge)
    assert res.ok, res
    assert r3_critical_trauma(Dispatch(unit_id=unit, incident_id="MCI-2",
                                       patient_ids=[most_unstable.id], target_hospital="A"),
                              surge).ok


# --- R4 ----------------------------------------------------------------------------------------

def test_r4_mutual_aid_limits(surge):
    assert r4_private_contracts(ActivateMutualAid(firm_id="MedRide", units=2), surge).ok
    over = r4_private_contracts(ActivateMutualAid(firm_id="MedRide", units=3), surge)
    assert not over.ok and over.code == "MUTUAL_AID_LIMIT"


def test_r4_mutual_aid_activates_units_after_delay(surge):
    assert surge.commit(ActivateMutualAid(firm_id="MedRide", units=2))
    assert not surge.unit_available("PVT-1")
    surge.run(until=36 + 10)
    assert surge.unit_available("PVT-1") and surge.unit_available("PVT-2")
    assert not surge.unit_available("PVT-3")
    again = r4_private_contracts(ActivateMutualAid(firm_id="MedRide", units=1), surge)
    assert not again.ok


def test_r4_private_hospital_contract(surge):
    unit = idle_unit(surge)
    serious = bus_patients(surge, Severity.SERIOUS)
    ok = r4_private_contracts(Dispatch(unit_id=unit, incident_id="MCI-2",
                                       patient_ids=[serious[0].id], target_hospital="D"), surge)
    assert ok.ok
    crit = bus_patients(surge, Severity.CRITICAL)[0]
    bad = r4_private_contracts(Dispatch(unit_id=unit, incident_id="MCI-2",
                                        patient_ids=[crit.id], target_hospital="D"), surge)
    assert not bad.ok and bad.code == "SEVERITY_NOT_ELIGIBLE"


def test_r4_contract_limit_and_no_surge():
    engine = Engine(generate(7, "surge"), None)
    engine.run(until=36)
    serious = bus_patients(engine, Severity.SERIOUS)
    for p in serious[:4]:  # four serious patients already arrived at D under contract
        p.hospital_id = "D"
    fifth = r4_private_contracts(RouteToHospital(unit_id="AMB-1", hospital_id="D"), engine)
    assert fifth.ok  # no patients on AMB-1 -> nothing to check
    unit = idle_unit(engine)
    over = r4_private_contracts(Dispatch(unit_id=unit, incident_id="MCI-2",
                                         patient_ids=[serious[4].id], target_hospital="D"),
                                engine)
    assert not over.ok and over.code == "CONTRACT_LIMIT"

    normal = Engine(generate(7, "normal"), None)
    normal.run(until=40)
    inc = next(iter(sorted(normal.active_incidents)), None)
    assert inc is not None
    p = normal.waiting_patients(inc)[0]
    res = r4_private_contracts(Dispatch(unit_id=idle_unit(normal), incident_id=inc,
                                        patient_ids=[p.id], target_hospital="D"), normal)
    assert not res.ok and res.code in ("NO_SURGE", "SEVERITY_NOT_ELIGIBLE")


# --- R5 ----------------------------------------------------------------------------------------

def test_r5_staging_warning_until_secured(surge):
    unit = idle_unit(surge)
    action = Dispatch(unit_id=unit, incident_id="MCI-1")
    shooting = surge.incidents["MCI-1"]
    assert not scene_entry_allowed(shooting)
    res = r5_scene_safety(action, surge)
    assert res.ok and res.level == "warn" and res.code == "STAGING"
    shooting.scene_secured = True
    assert scene_entry_allowed(shooting)
    assert r5_scene_safety(action, surge).level == "pass"


# --- R6 ----------------------------------------------------------------------------------------

def test_r6_review_for_detour_and_waiting(surge):
    unit = idle_unit(surge)
    crit = bus_patients(surge, Severity.CRITICAL, trauma=True)[0]
    etas = {h: surge.expected_arrival(Dispatch(unit_id=unit, incident_id="MCI-2",
                                               patient_ids=[crit.id]), h) for h in ("A", "C")}
    near, far = sorted(etas, key=etas.get)
    near_res = r6_human_review(Dispatch(unit_id=unit, incident_id="MCI-2",
                                        patient_ids=[crit.id], target_hospital=near), surge)
    assert near_res.level == "pass"
    saturate_trauma(surge, near)
    waiting = r6_human_review(Dispatch(unit_id=unit, incident_id="MCI-2",
                                       patient_ids=[crit.id], target_hospital=near), surge)
    assert waiting.ok and waiting.level == "review" and "R6a" in waiting.code


# --- R7 ----------------------------------------------------------------------------------------

def test_r7_pass_and_fail(surge):
    unit = idle_unit(surge)
    minors = bus_patients(surge, Severity.MINOR)
    crit = bus_patients(surge, Severity.CRITICAL)[0]
    assert r7_ambulance_capacity(Dispatch(unit_id=unit, incident_id="MCI-2",
                                          patient_ids=[m.id for m in minors[:2]]), surge).ok
    bad = r7_ambulance_capacity(Dispatch(unit_id=unit, incident_id="MCI-2",
                                         patient_ids=[crit.id, minors[0].id]), surge)
    assert not bad.ok and bad.code == "CRITICAL_NOT_ALONE"


# --- R8 ----------------------------------------------------------------------------------------

def test_r8_pass_and_fail(surge):
    assert r8_staff_loans(LendStaff(lender_id="A", borrower_id="C", nurses=1), surge).ok
    assert r8_staff_loans(LendStaff(lender_id="A", borrower_id="A", nurses=1), surge).code == \
        "SELF_LOAN"
    breach = r8_staff_loans(LendStaff(lender_id="A", borrower_id="C", nurses=7), surge)
    assert not breach.ok and breach.code == "BELOW_COVERAGE"


def test_r8_borrowed_nurses_cannot_be_lent_on(surge):
    c = surge.hospitals["C"]
    c.nurses_loaned_in = 4  # borrowed from elsewhere
    own_spare = c.config.nurses_total - c.config.min_nurse_coverage
    res = r8_staff_loans(LendStaff(lender_id="C", borrower_id="B", nurses=own_spare + 1), surge)
    assert not res.ok


# --- R9 ----------------------------------------------------------------------------------------

def test_r9_pass_and_fail(surge):
    assert r9_known_action(LendStaff(lender_id="A", borrower_id="C", nurses=1), surge).ok

    class AddBeds:
        kind = "add_beds"

    res = r9_known_action(AddBeds(), surge)
    assert not res.ok and res.code == "UNKNOWN_ACTION"
    assert not surge.commit(AddBeds())


def test_r9_actions_reject_extra_fields():
    with pytest.raises(ValueError):
        Dispatch(unit_id="AMB-1", incident_id="I-1", er_beds_total=99)
