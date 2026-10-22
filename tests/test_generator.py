import os
import subprocess
import sys
from pathlib import Path

from sim.engine import Engine
from sim.entities import IncidentType, Owner, Severity
from sim.generator import BUS_VICTIMS, generate, load, save, to_json
from sim.town import TownProfile
from tests.helpers import GreedyTestPolicy
from tests.invariants import check_invariants

ROOT = Path(__file__).resolve().parent.parent


def test_cli_writes_valid_surge_scenario(tmp_path):
    out = subprocess.run(
        [sys.executable, "-m", "sim.generator", "--seed", "7", "--demand", "surge",
         "--out", str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    path = tmp_path / "seed_07_surge.json"
    assert path.exists() and "wrote" in out.stdout
    sc = load(path)
    assert sc.seed == 7 and sc.demand == "surge"


def test_byte_identical_across_hash_seeds(tmp_path):
    files = []
    for hash_seed in ("1", "2"):
        d = tmp_path / hash_seed
        subprocess.run(
            [sys.executable, "-m", "sim.generator", "--seed", "7", "--demand", "surge",
             "--out", str(d)],
            cwd=ROOT, check=True, env={**os.environ, "PYTHONHASHSEED": hash_seed},
        )
        files.append((d / "seed_07_surge.json").read_bytes())
    assert files[0] == files[1]


def test_surge_contains_exact_normal_stream():
    normal, surge = generate(7, "normal"), generate(7, "surge")
    surge_normal_inc = [i for i in surge.incidents if not i.id.startswith("MCI-")]
    assert [i.model_dump() for i in surge_normal_inc] == [i.model_dump() for i in normal.incidents]
    surge_normal_pat = [p for p in surge.patients if not p.incident_id.startswith("MCI-")]
    assert [p.model_dump() for p in surge_normal_pat] == [p.model_dump() for p in normal.patients]
    assert surge.initial_occupancy == normal.initial_occupancy
    assert [a.model_dump() for a in surge.ambulances] == [a.model_dump() for a in normal.ambulances]


def test_surge_mci_composition():
    for seed in range(5):
        sc = generate(seed, "surge")
        inc = {i.id: i for i in sc.incidents}
        shooting, bus = inc["MCI-1"], inc["MCI-2"]
        assert shooting.type == IncidentType.SHOOTING and shooting.call_tick == 30
        assert shooting.violent and not shooting.scene_secured
        assert 5 <= shooting.secure_delay_min <= 15
        assert bus.type == IncidentType.BUS_CRASH and bus.call_tick == 35
        assert BUS_VICTIMS[0] <= len(bus.true_victim_ids) <= BUS_VICTIMS[1]
        pats = {p.id: p for p in sc.patients}
        minors = [p for p in bus.true_victim_ids if pats[p].true_severity == Severity.MINOR]
        walk = [w for w in sc.walk_ins if pats[w.patient_id].incident_id == "MCI-2"]
        assert 0.45 <= len(walk) / len(minors) <= 0.65
        assert all(30 <= w.tick - 35 + 15 <= 60 for w in walk)  # call + 15..45
        assert abs(bus.reported_victims - len(bus.true_victim_ids)) <= 0.2 * len(
            bus.true_victim_ids) + 1


def test_infrastructure_derived_from_town_profile():
    sc = generate(3, "normal")
    town = TownProfile()
    h = {x.id: x for x in sc.hospitals}
    assert sc.population == 50_000 and sc.town == town.summary()
    assert {k: h[k].er_beds_total for k in "ABCD"} == town.er_beds
    assert {k: h[k].ward_beds_total for k in "ABCD"} == town.ward_beds
    assert {k: h[k].nurses_total for k in "ABCD"} == town.ed_nurses
    assert h["A"].trauma_surgeons_total == 1 and h["C"].trauma_surgeons_total == 1
    assert h["B"].stabilization_only and h["B"].trauma_surgeons_total == 0
    assert h["D"].owner == Owner.PRIVATE and h["D"].surge_contract.max_surge_patients == 4
    assert {a.id for a in sc.ambulances if a.owner == Owner.PUBLIC} == {
        f"AMB-{i}" for i in range(1, 5)}
    assert sc.firms[0].max_mutual_aid_units == 2 and sc.firms[0].activation_minutes == 10
    assert all(0.5 <= v <= 0.8 for v in sc.initial_occupancy.values())
    assert all(0.65 <= v <= 0.8 for v in sc.initial_ward_occupancy.values())
    assert all(x.min_nurse_coverage * 2 >= x.nurses_total for x in sc.hospitals)


def test_everything_inside_the_town_square():
    sc = generate(5, "surge")
    town = TownProfile()
    points = [i.location for i in sc.incidents] + [h.location for h in sc.hospitals] + [
        a.home_station for a in sc.ambulances]
    for lat, lon in points:
        x, y = town.to_km(lat, lon)
        assert -1e-6 <= x <= 20 + 1e-6 and -1e-6 <= y <= 20 + 1e-6


def test_population_changes_town_and_file_name(tmp_path):
    big = generate(7, "normal", population=200_000)
    assert big.town["city_ambulances"] > generate(7, "normal").town["city_ambulances"]
    assert save(big, tmp_path).name == "seed_07_normal_p200000.json"


def test_save_load_roundtrip(tmp_path):
    sc = generate(11, "surge")
    path = save(sc, tmp_path)
    assert to_json(load(path)) == to_json(sc)


def test_generated_surge_runs_with_invariants():
    engine = Engine(generate(7, "surge"), GreedyTestPolicy(), tick_hook=check_invariants)
    engine.run()
    assert engine.tick == engine.end_tick
