import pytest

from sim.actions import Dispatch, LendStaff, RouteToHospital
from sim.engine import Engine, R9Violation
from sim.entities import AmbulanceState, PatientStatus, Severity
from sim.events import EventType
from sim.hospital import HospitalState, QueueItem
from sim.travel import TimingConfig
from tests.helpers import (
    GreedyTestPolicy,
    hospital,
    mini_scenario,
    patient_done,
    stress_scenario,
)
from tests.invariants import check_invariants

A = AmbulanceState
TRAUMA_DEMAND = {"er_bed": 0, "trauma_bay": 1, "or": 0, "surgeon": 1, "nurse_slot": 2}


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


def fill_er(engine, hid, until=500):
    hs = engine.hospitals[hid]
    while hs.free("er_bed") > 0:
        hs.add_background_patient(engine.tick, until, in_treatment=True)
    for t in hs.treatments:  # nothing frees before `until`
        t.end_tick = until


def test_mini_scenario_full_lifecycle_exact_timestamps():
    """Hand-computed with deterministic timing (zero noise, lower-bound durations):
    station->scene 11.1 km = 19 min; scene->hospital 5.6 km = 10 min; hospital->station
    (non-emergency) = 12 min; scene time 5 (serious), loading 3, offload band 5 (ER empty;
    patient admitted on arrival), handover 5, ER treatment 60.
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


def test_log_supports_metrics():
    engine = run_lifecycle()
    started = engine.log.of_type(EventType.RUN_STARTED)
    assert len(started) == 1 and started[0].payload["patients"][0]["id"] == "P-1"
    treated = [e for e in engine.log.of_type(EventType.PATIENT_STATE_CHANGED)
               if e.payload["to"] == PatientStatus.IN_TREATMENT]
    assert "survival_prob" in treated[0].payload
    summaries = engine.log.of_type(EventType.RUN_SUMMARY)
    assert len(summaries) == 1 and summaries[0].payload["patients"][0]["survival_prob"]


def test_run_summary_emitted_once_across_partial_runs():
    engine = Engine(mini_scenario(), LifecyclePolicy(), timing=TimingConfig.deterministic())
    engine.run(until=30)
    engine.run(until=60)
    assert not engine.log.of_type(EventType.RUN_SUMMARY)
    engine.run()
    engine.run()
    assert len(engine.log.of_type(EventType.RUN_SUMMARY)) == 1


def test_stress_scenario_invariants_every_tick():
    engine = Engine(stress_scenario(), GreedyTestPolicy(), tick_hook=check_invariants)
    engine.run()
    assert all(patient_done(p) for p in engine.patients.values())
    assert engine.log.of_type(EventType.SCENE_SECURED)
    changes = engine.log.of_type(EventType.UNIT_STATE_CHANGED)
    assert any(e.payload.get("to") == A.STAGING for e in changes)
    secured_tick = engine.log.of_type(EventType.SCENE_SECURED)[0].tick
    on_scene_i2 = [e.tick for e in changes
                   if e.payload["kind"] == "AMBULANCE" and e.payload.get("to") == A.ON_SCENE
                   and e.payload.get("incident_id") == "I-2"]
    assert on_scene_i2 and min(on_scene_i2) > secured_tick
    fire_on = [e.tick for e in changes
               if e.payload.get("unit_id") == "FIRE-1" and e.payload.get("to") == "ON_SCENE"]
    load_i3 = [e.tick for e in changes
               if e.payload.get("to") == A.LOADING and e.payload.get("incident_id") == "I-3"]
    assert fire_on and load_i3 and min(load_i3) >= fire_on[0] + 12


def test_same_seed_same_log():
    def events(seed):
        e = Engine(stress_scenario(seed), GreedyTestPolicy())
        e.run()
        return [ev.model_dump(mode="json") for ev in e.log.events]

    assert events(3) == events(3)
    assert events(3) != events(4)


def test_policy_choice_does_not_shift_outside_randomness():
    """Paired design: background arrivals and per-patient durations are policy-independent."""
    def run(policy):
        e = Engine(stress_scenario(), policy)
        e.run()
        return e, [hs.background_seq for hs in e.hospitals.values()]

    greedy, bg_greedy = run(GreedyTestPolicy())
    idle, bg_idle = run(None)
    assert bg_greedy == bg_idle
    assert greedy.patient_u == idle.patient_u


def test_crew_triage_clears_destination_validated_for_other_patients():
    engine = Engine(stress_scenario(), None, tick_hook=check_invariants)
    engine.run(until=30)
    assert engine.commit(Dispatch(unit_id="AMB-2", incident_id="I-5", patient_ids=["I-5-P3"],
                                  target_hospital="B"))
    # The named minor patient is gone before the unit arrives; the crew triages someone else.
    engine.patients["I-5-P3"].status = PatientStatus.DECEASED
    engine.ambulances["AMB-2"].assigned_patient_ids = []
    engine.run(until=80)
    loading = [e for e in engine.log.of_type(EventType.UNIT_STATE_CHANGED)
               if e.payload.get("unit_id") == "AMB-2" and e.payload.get("to") == A.LOADING]
    assert loading and loading[0].payload["crew_triage"]
    assert loading[0].payload["destination_cleared"]
    assert engine.patients["I-5-P0"].hospital_id != "B"


def test_r9_policy_mutating_state_raises():
    class Cheater:
        name = "cheater"

        def decide(self, engine):
            engine.hospitals["A"].config.er_beds_total += 5
            return []

    engine = Engine(stress_scenario(), Cheater())
    with pytest.raises(R9Violation):
        engine.run(until=2)
    assert engine.log.events[-1].payload["rule_id"] == "R9"


def test_crew_waits_until_patient_admitted():
    engine = Engine(stress_scenario(), GreedyTestPolicy(), tick_hook=check_invariants)
    engine.run(until=0)
    fill_er(engine, "A", until=150)
    fill_er(engine, "B", until=150)
    engine.run()
    cared = {}  # patient -> tick admitted (or died)
    for e in engine.log.of_type(EventType.PATIENT_STATE_CHANGED):
        if e.payload["to"] in (PatientStatus.IN_TREATMENT, PatientStatus.DECEASED):
            cared.setdefault(e.payload["patient_id"], e.tick)
    onboard, band_end, extended = {}, {}, 0
    for e in engine.log.of_type(EventType.UNIT_STATE_CHANGED):
        if e.payload.get("to") == A.TRANSPORTING:
            onboard[e.payload["unit_id"]] = e.payload["patient_ids"]
        if e.payload.get("to") == A.WAITING_AT_ER:
            band_end[e.payload["unit_id"]] = e.tick + e.payload["band_minutes"]
        if e.payload.get("to") == A.HANDOVER:
            for pid in onboard[e.payload["unit_id"]]:
                assert cared[pid] <= e.tick, f"{pid} handed over before admission"
            extended += e.tick > band_end[e.payload["unit_id"]]
    assert extended  # at least one crew waited beyond the crowding band for a bed


def test_hospital_bay_then_or_then_discharge():
    hs = HospitalState(config=hospital())
    hs.enqueue(QueueItem(id="P", severity=Severity.CRITICAL, demand=TRAUMA_DEMAND,
                         needs_or=True, arrival_tick=0,
                         durations={"bay": 30, "or": 60, "er": 0}))
    assert hs.admit_from_queue(0) == ["P"]
    assert hs.occupied["trauma_bay"] == 1
    assert hs.finish_treatments(30) == []
    assert hs.occupied["trauma_bay"] == 0 and hs.occupied["or"] == 1
    assert hs.finish_treatments(90) == ["P"]
    assert all(v == 0 for v in hs.occupied.values())


def test_projected_surgeons_stay_busy_through_or_phase():
    hs = HospitalState(config=hospital(trauma_bays_total=2, ors_total=2,
                                       trauma_surgeons_total=2))
    for i in range(2):
        hs.enqueue(QueueItem(id=f"C{i}", severity=Severity.CRITICAL, demand=TRAUMA_DEMAND,
                             needs_or=True, arrival_tick=0,
                             durations={"bay": 30, "or": 120, "er": 0}))
    hs.admit_from_queue(0)
    assert hs.projected_free("surgeon", 40, []) == 0
    assert hs.projected_free("trauma_bay", 40, []) == 2
    hs.finish_treatments(30)
    assert hs.free("surgeon") == 0


def test_critical_not_starved_by_minor_stream():
    hs = HospitalState(config=hospital(nurses_total=1, er_beds_total=10))  # 4 nurse slots
    for i in range(4):
        hs.add_background_patient(0, 10 + i, in_treatment=True)  # one slot frees per tick
    hs.enqueue(QueueItem(id="CRIT", severity=Severity.CRITICAL, demand=TRAUMA_DEMAND,
                         arrival_tick=0, durations={"bay": 30, "or": 0, "er": 0}))
    admitted_at = None
    for t in range(1, 200):
        hs.finish_treatments(t)
        hs.add_background_patient(t, 60, in_treatment=False)
        if "CRIT" in hs.admit_from_queue(t):
            admitted_at = t
            break
    assert admitted_at is not None and admitted_at <= 12


def test_staff_loan_respects_coverage_and_returns():
    engine = Engine(stress_scenario(), None, timing=TimingConfig.deterministic(),
                    tick_hook=check_invariants)
    engine.run(until=1)
    a = engine.hospitals["A"]
    assert a.can_lend(2) and not a.can_lend(5)  # 8 nurses, min coverage 4
    assert engine.commit(LendStaff(lender_id="A", borrower_id="B", nurses=2))
    assert engine.hospitals["A"].nurses_loaned_out == 2
    engine.run(until=1 + 20)
    assert engine.hospitals["B"].nurses_loaned_in == 2
    engine.run(until=1 + 20 + 120 + 100)
    assert engine.hospitals["B"].nurses_loaned_in == 0
    assert engine.hospitals["A"].nurses_loaned_out == 0
    phases = [e.payload["phase"] for e in engine.log.of_type(EventType.STAFF_LOAN)]
    assert phases == ["DEPARTED", "ARRIVED", "RETURNED"]


SERIOUS_ER = {"er_bed": 1, "trauma_bay": 0, "or": 0, "surgeon": 0, "nurse_slot": 1,
              "ward_bed": 0}


def ward_hospital(ward_beds=1):
    return HospitalState(config=hospital(ward_beds_total=ward_beds, er_beds_total=2))


def test_serious_patient_boards_in_er_when_ward_full_then_moves():
    hs = ward_hospital(ward_beds=1)
    assert hs.add_background_ward_patient(0, 500, remaining=100, force=True)  # ward full to t=100
    hs.enqueue(QueueItem(id="S", severity=Severity.SERIOUS, demand=SERIOUS_ER, arrival_tick=0,
                         durations={"bay": 0, "or": 0, "er": 60}, needs_ward=True))
    assert hs.admit_from_queue(0) == ["S"]
    assert hs.finish_treatments(60) == []
    assert hs.last_moves == [("S", "boarding")]
    assert hs.occupied["er_bed"] == 1 and hs.snapshot()["boarding"] == 1  # keeps the ER bed
    hs.finish_treatments(100)  # background inpatient leaves at t=100
    hs.finish_treatments(101)  # boarders are served first on the next tick
    assert hs.last_moves == [("S", "ward")]
    assert hs.occupied["er_bed"] == 0 and hs.occupied["ward_bed"] == 1 and not hs.boarders


def test_boarder_blocks_er_bed_for_next_patient():
    hs = ward_hospital(ward_beds=0)
    hs.config.er_beds_total = 1
    for pid in ("S1", "S2"):
        hs.enqueue(QueueItem(id=pid, severity=Severity.SERIOUS, demand=SERIOUS_ER,
                             arrival_tick=0, durations={"bay": 0, "or": 0, "er": 30},
                             needs_ward=True))
    assert hs.admit_from_queue(0) == ["S1"]
    hs.finish_treatments(30)  # S1 boards: no ward beds at all
    assert hs.admit_from_queue(30) == []  # S2 cannot get the ER bed
    assert hs.projected_free("er_bed", 500, []) < 1


def test_minor_patient_goes_home_without_ward_bed():
    hs = ward_hospital(ward_beds=0)
    hs.enqueue(QueueItem(id="M", severity=Severity.MINOR, demand=SERIOUS_ER, arrival_tick=0,
                         durations={"bay": 0, "or": 0, "er": 30}))
    hs.admit_from_queue(0)
    assert hs.finish_treatments(30) == ["M"]
    assert hs.occupied["er_bed"] == 0
