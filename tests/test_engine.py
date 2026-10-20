import numpy as np

from sim.actions import Dispatch, LendStaff, RouteToHospital
from sim.engine import Engine
from sim.entities import AmbulanceState, PatientStatus, Severity
from sim.events import EventType
from sim.hospital import HospitalState, QueueItem
from sim.travel import Sampler, TimingConfig
from tests.helpers import (
    GreedyTestPolicy,
    hospital,
    mini_scenario,
    patient_done,
    stress_scenario,
)
from tests.invariants import check_invariants

A = AmbulanceState


class LifecyclePolicy:
    """Dispatch AMB-1 to I-1 when called; route to H once the unit is on scene."""

    name = "lifecycle"

    def decide(self, engine):
        actions = []
        if "I-1" in engine.active_incidents and engine.ambulances["AMB-1"].state == A.IDLE \
                and engine.patients["P-1"].ambulance_id is None:
            actions.append(Dispatch(unit_id="AMB-1", incident_id="I-1", patient_ids=["P-1"]))
        if engine.units_needing_destination():
            actions.append(RouteToHospital(unit_id="AMB-1", hospital_id="H"))
        return actions


def run_lifecycle():
    engine = Engine(mini_scenario(), LifecyclePolicy(), timing=TimingConfig.deterministic(),
                    tick_hook=check_invariants)
    engine.run()
    return engine


def test_mini_scenario_full_lifecycle_exact_timestamps():
    """Hand-computed with deterministic timing (zero noise, lower-bound durations):
    station->scene 11.1 km = 19 min; scene->hospital 5.6 km = 10 min; hospital->station
    (non-emergency) = 12 min; scene time 5 (serious), loading 3, offload 5 (ER empty),
    handover 5, ER treatment 60.
    """
    engine = run_lifecycle()
    amb_changes = [
        (e.tick, e.payload["from"], e.payload["to"])
        for e in engine.log.of_type(EventType.UNIT_STATE_CHANGED)
        if e.payload["unit_id"] == "AMB-1"
    ]
    assert amb_changes == [
        (2, A.IDLE, A.EN_ROUTE),
        (21, A.EN_ROUTE, A.ON_SCENE),
        (26, A.ON_SCENE, A.LOADING),
        (29, A.LOADING, A.TRANSPORTING),
        (39, A.TRANSPORTING, A.WAITING_AT_ER),
        (44, A.WAITING_AT_ER, A.HANDOVER),
        (49, A.HANDOVER, A.RETURNING),
        (61, A.RETURNING, A.IDLE),
    ]
    p = engine.patients["P-1"]
    ts = p.timestamps
    assert (ts.call, ts.unit_on_scene, ts.loaded, ts.arrived_hospital,
            ts.definitive_care_start, ts.discharged) == (2, 21, 29, 39, 39, 99)
    assert p.status == PatientStatus.DISCHARGED
    amb = engine.ambulances["AMB-1"]
    assert amb.location == amb.home_station and amb.assigned_incident is None
    hs = engine.hospitals["H"]
    assert all(v == 0 for v in hs.occupied.values()) and not hs.queue
    assert len(engine.log.of_type(EventType.SCENE_REPORT)) == 1
    assert len(engine.log.of_type(EventType.COMMITTED)) == 2


def test_stress_scenario_invariants_every_tick():
    engine = Engine(stress_scenario(), GreedyTestPolicy(), tick_hook=check_invariants)
    engine.run()
    assert all(patient_done(p) for p in engine.patients.values())
    types = {e.type for e in engine.log.events}
    assert EventType.SCENE_SECURED in types
    staged = [e for e in engine.log.of_type(EventType.UNIT_STATE_CHANGED)
              if e.payload.get("to") == A.STAGING]
    assert staged, "an ambulance should stage at the violent scene"
    secured_tick = engine.log.of_type(EventType.SCENE_SECURED)[0].tick
    on_scene_i2 = [e.tick for e in engine.log.of_type(EventType.UNIT_STATE_CHANGED)
                   if e.payload["kind"] == "AMBULANCE" and e.payload.get("to") == A.ON_SCENE
                   and e.payload.get("incident_id") == "I-2"]
    assert on_scene_i2 and min(on_scene_i2) > secured_tick
    # Extrication: no loading at I-3 before fire finishes.
    fire_on = [e.tick for e in engine.log.of_type(EventType.UNIT_STATE_CHANGED)
               if e.payload.get("unit_id") == "FIRE-1" and e.payload.get("to") == "ON_SCENE"]
    load_i3 = [e.tick for e in engine.log.of_type(EventType.UNIT_STATE_CHANGED)
               if e.payload.get("to") == A.LOADING and e.payload.get("incident_id") == "I-3"]
    assert fire_on and load_i3 and min(load_i3) >= fire_on[0] + 12


def test_same_seed_same_log():
    def events(seed):
        e = Engine(stress_scenario(seed), GreedyTestPolicy())
        e.run()
        return [ev.model_dump(mode="json") for ev in e.log.events]

    assert events(3) == events(3)
    assert events(3) != events(4)


def test_validator_rejects_double_dispatch_and_overcapacity():
    engine = Engine(stress_scenario(), None, tick_hook=check_invariants)
    engine.run(until=30)
    p_crit = "I-5-P0"
    ok = engine.commit(Dispatch(unit_id="AMB-1", incident_id="I-5",
                                patient_ids=[p_crit, "I-5-P1"]))
    assert not ok  # R7: critical must travel alone
    assert engine.log.events[-1].payload["rule_id"] == "R7"
    assert engine.commit(Dispatch(unit_id="AMB-1", incident_id="I-5", patient_ids=[p_crit]))
    assert not engine.commit(Dispatch(unit_id="AMB-1", incident_id="I-5",
                                      patient_ids=["I-5-P1"]))  # R1: already this tick
    assert not engine.commit(Dispatch(unit_id="AMB-2", incident_id="I-5",
                                      patient_ids=[p_crit]))  # R1: patient taken
    check_invariants(engine)


def test_r2_rejects_full_hospital_when_another_has_space():
    engine = Engine(stress_scenario(), None)
    engine.run(until=30)
    b = engine.hospitals["B"]
    sampler = Sampler(np.random.default_rng(0), TimingConfig.deterministic())
    while b.free("er_bed") > 0:
        b.add_background_patient(engine.tick, sampler, in_treatment=True, remaining=500)
    for t in b.treatments:  # nothing frees before the ETA
        t.end_tick = 500
    engine.commit(Dispatch(unit_id="AMB-3", incident_id="I-5", patient_ids=["I-5-P3"],
                           target_hospital="B"))
    assert engine.log.events[-1].type == EventType.PROPOSAL_REJECTED
    assert engine.log.events[-1].payload["rule_id"] == "R2"
    assert engine.commit(Dispatch(unit_id="AMB-3", incident_id="I-5", patient_ids=["I-5-P3"],
                                  target_hospital="A"))


def test_hospital_bay_then_or_then_discharge():
    hs = HospitalState(config=hospital())
    sampler = Sampler(np.random.default_rng(0), TimingConfig.deterministic())
    hs.enqueue(QueueItem(id="P", severity=Severity.CRITICAL,
                         demand={"er_bed": 0, "trauma_bay": 1, "or": 0, "surgeon": 1,
                                 "nurse_slot": 2}, needs_or=True, arrival_tick=0))
    assert hs.admit_from_queue(0, sampler) == ["P"]
    assert hs.occupied["trauma_bay"] == 1
    assert hs.finish_treatments(30, sampler) == []
    assert hs.occupied["trauma_bay"] == 0 and hs.occupied["or"] == 1
    assert hs.finish_treatments(90, sampler) == ["P"]
    assert all(v == 0 for v in hs.occupied.values())


def test_staff_loan_respects_coverage_and_returns():
    engine = Engine(stress_scenario(), None, timing=TimingConfig.deterministic(),
                    tick_hook=check_invariants)
    engine.run(until=1)
    a = engine.hospitals["A"]
    assert a.can_lend(2) and not a.can_lend(5)  # 8 nurses, min coverage 4, some slots busy
    assert engine.commit(LendStaff(lender_id="A", borrower_id="B", nurses=2))
    assert engine.hospitals["A"].nurses_loaned_out == 2
    engine.run(until=1 + 20)
    assert engine.hospitals["B"].nurses_loaned_in == 2
    engine.run(until=1 + 20 + 120)
    assert engine.hospitals["B"].nurses_loaned_in == 0
    assert engine.hospitals["A"].nurses_loaned_out == 0


def test_r2_all_full_clause_allows_queueing():
    engine = Engine(stress_scenario(), None)
    engine.run(until=30)
    sampler = Sampler(np.random.default_rng(0), TimingConfig.deterministic())
    for hs in engine.hospitals.values():
        while hs.free("er_bed") > 0:
            hs.add_background_patient(engine.tick, sampler, in_treatment=True, remaining=500)
        for t in hs.treatments:
            t.end_tick = 500
    assert engine.commit(Dispatch(unit_id="AMB-3", incident_id="I-5", patient_ids=["I-5-P3"],
                                  target_hospital="B"))
    validated = engine.log.of_type(EventType.PROPOSAL_VALIDATED)[-1]
    assert "all-full clause" in validated.payload["notes"][0]
