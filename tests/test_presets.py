import pytest

from baselines.nearest import NearestPolicy
from sim.engine import Engine
from sim.entities import IncidentType, Severity
from sim.presets import PRESETS, START_TICK, build_preset
from sim.travel import haversine_km
from tests.invariants import check_invariants


@pytest.mark.parametrize("name", list(PRESETS))
def test_every_preset_runs_with_invariants(name):
    engine = Engine(build_preset(name), NearestPolicy(), tick_hook=check_invariants)
    engine.run()
    assert engine.tick == engine.end_tick


@pytest.mark.parametrize("name,itype,victims", [
    ("Cardiac arrest", IncidentType.MEDICAL_CARDIAC, 1),
    ("Two-car crash", IncidentType.VEHICLE_CRASH, 3),
    ("Shooting", IncidentType.SHOOTING, 2),
])
def test_single_incident_presets(name, itype, victims):
    sc = build_preset(name)
    assert len(sc.incidents) == 1
    inc = sc.incidents[0]
    assert inc.type == itype and len(inc.true_victim_ids) == victims
    assert inc.call_tick == START_TICK


def test_cardiac_patient_needs_a_cath_lab_hospital():
    sc = build_preset("Cardiac arrest")
    p = sc.patients[0]
    assert p.true_severity == Severity.CRITICAL and p.needs.capability == "CARDIAC_CATH"


def test_bus_crash_walk_ins_go_to_nearest_hospital():
    sc = build_preset("School bus crash")
    bus = sc.incidents[0]
    nearest = min(sc.hospitals, key=lambda h: haversine_km(h.location, bus.location))
    assert sc.walk_ins and all(w.hospital_id == nearest.id for w in sc.walk_ins)
    assert all(START_TICK + 15 <= w.tick <= START_TICK + 45 for w in sc.walk_ins)


def test_presets_are_deterministic():
    assert build_preset("Two-car crash") == build_preset("Two-car crash")
