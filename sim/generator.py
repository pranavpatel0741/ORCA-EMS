"""Seeded scenario generator (PLAN §10).

    python -m sim.generator --seed 7 --demand surge

Writes `data/scenarios/seed_{seed:02d}_{demand}.json`. The file does not depend on the
information setting, which is chosen at run time.

Every random draw uses `default_rng([seed, STREAM])` with a fixed stream id, so files are
reproducible and the surge file for a seed contains *exactly* the normal-demand stream for that
seed plus the two mass-casualty incidents (paired comparison for H3).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from config.settings import DATA_DIR
from sim.entities import (
    Ambulance,
    AmbulanceState,
    Capability,
    Hospital,
    Incident,
    IncidentType,
    Owner,
    Patient,
    PatientNeeds,
    PatientTimestamps,
    PrivateFirm,
    ResponderTeam,
    Scenario,
    Severity,
    SurgeContract,
    TeamKind,
    UnitType,
    WalkIn,
)
from sim.town import TownProfile
from sim.travel import haversine_km

STREAM = {
    "occupancy": 10,
    "busy_units": 11,
    "arrivals": 12,
    "severity": 13,
    "mci": 14,
    "reported": 15,
    "walk_ins": 16,
    "scene": 17,
    "narrative": 18,
    "mci_scene": 19,
}

HORIZON = 180
DRAIN = 120

SHOOTING_TICK = 30
BUS_CRASH_TICK = 35
BUS_VICTIMS = (28, 34)
BUS_MIX = {  # START-style share ranges (PLAN §10); minor takes the remainder
    Severity.CRITICAL: (0.15, 0.20),
    Severity.SERIOUS: (0.30, 0.35),
    Severity.EXPECTANT: (0.00, 0.05),
}
WARD_OCCUPANCY = (0.65, 0.80)  # starting inpatient occupancy (assumption, typical U.S. range)
WALK_IN_SHARE = (0.50, 0.60)
WALK_IN_DELAY = (15, 45)
OR_NEED_PROB = 0.5  # share of critical trauma patients who need an OR within 60 min
BUSY_UNIT_PROB = 0.3

NORMAL_MIX = {
    IncidentType.MEDICAL_CARDIAC: 0.20,
    IncidentType.MEDICAL_STROKE: 0.15,
    IncidentType.MEDICAL_GENERAL: 0.30,
    IncidentType.FALL: 0.20,
    IncidentType.VEHICLE_CRASH: 0.15,
}
SEVERITY_MIX = {
    IncidentType.MEDICAL_CARDIAC: {Severity.CRITICAL: 0.4, Severity.SERIOUS: 0.6},
    IncidentType.MEDICAL_STROKE: {Severity.CRITICAL: 0.4, Severity.SERIOUS: 0.6},
    IncidentType.MEDICAL_GENERAL: {Severity.SERIOUS: 0.4, Severity.MINOR: 0.6},
    IncidentType.FALL: {Severity.SERIOUS: 0.3, Severity.MINOR: 0.7},
    IncidentType.VEHICLE_CRASH: {Severity.CRITICAL: 0.25, Severity.SERIOUS: 0.40,
                                 Severity.MINOR: 0.35},
}
TWO_PATIENT_PROB = {IncidentType.VEHICLE_CRASH: 0.5}
DEFAULT_TWO_PATIENT_PROB = 0.15
EXTRICATION_PROB = 0.25

# Town layout as fractions of the town side (x east, y north from the SW corner).
HOSPITAL_LAYOUT = {"A": (0.50, 0.55), "B": (0.25, 0.75), "C": (0.75, 0.25), "D": (0.20, 0.35)}
STATION_LAYOUT = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]
PRIVATE_BASE = (0.50, 0.20)
POLICE_LAYOUT = [(0.50, 0.50), (0.40, 0.62), (0.62, 0.40)]
FIRE_LAYOUT = [(0.55, 0.45), (0.45, 0.30)]
DEFAULT_POPULATION = 50_000


# --- infrastructure derived from the town profile ------------------------------------------------


def hospitals(town: TownProfile) -> list[Hospital]:
    """Four hospital roles; every count comes from `TownProfile` (see sim/town.py)."""
    er, ward, nurses = town.er_beds, town.ward_beds, town.ed_nurses
    ors, bays, surgeons = town.operating_rooms, town.trauma_bays, town.surgical_teams
    C = Capability

    def h(hid, owner, caps, bays_n, ors_n, surgeons_n, **kw) -> Hospital:
        return Hospital(id=hid, name=f"Hospital {hid}", location=town.scale(*HOSPITAL_LAYOUT[hid]),
                        owner=owner, capabilities=set(caps), er_beds_total=er[hid],
                        trauma_bays_total=bays_n, ors_total=ors_n,
                        trauma_surgeons_total=surgeons_n, nurses_total=nurses[hid],
                        min_nurse_coverage=math.ceil(nurses[hid] / 2),
                        ward_beds_total=ward[hid], **kw)

    return [
        h("A", Owner.PUBLIC, [C.TRAUMA_L1, C.CARDIAC_CATH, C.STROKE, C.GENERAL],
          bays["A"], ors["A"], surgeons["A"]),
        h("B", Owner.PUBLIC, [C.GENERAL], 1, 0, 0, stabilization_only=True),
        h("C", Owner.PUBLIC, [C.TRAUMA_L2, C.CARDIAC_CATH, C.GENERAL],
          bays["C"], ors["C"], surgeons["C"]),
        h("D", Owner.PRIVATE, [C.GENERAL], 0, ors["D"], 0,
          surge_contract=SurgeContract(max_surge_patients=4,
                                       eligible_severities={Severity.SERIOUS},
                                       accepts_critical_trauma=False)),
    ]


def fleet(town: TownProfile, rng: np.random.Generator) -> tuple[list[Ambulance], list[PrivateFirm]]:
    ambulances = []
    for i in range(town.city_ambulances):
        home = town.scale(*STATION_LAYOUT[i % len(STATION_LAYOUT)])
        utype = UnitType.ALS if i < town.als_units else UnitType.BLS
        amb = Ambulance(id=f"AMB-{i + 1}", owner=Owner.PUBLIC, unit_type=utype,
                        home_station=home, location=home)
        # Some units start busy: returning from an earlier job (the only allowed busy state).
        if rng.random() < BUSY_UNIT_PROB:
            amb.state = AmbulanceState.RETURNING
            amb.state_until_tick = int(rng.integers(5, 26))
            amb.location = _random_point(rng, town)
        ambulances.append(amb)
    base = town.scale(*PRIVATE_BASE)
    private_ids = [f"PVT-{i + 1}" for i in range(town.private_units)]
    for uid in private_ids:
        ambulances.append(Ambulance(id=uid, owner=Owner.PRIVATE, unit_type=UnitType.BLS,
                                    home_station=base, location=base, firm_id="MedRide"))
    firm = PrivateFirm(id="MedRide", name="MedRide", unit_ids=private_ids,
                       max_mutual_aid_units=min(2, len(private_ids)), activation_minutes=10)
    return ambulances, [firm]


def teams(town: TownProfile) -> list[ResponderTeam]:
    out = []
    for kind, n, layout, prefix in ((TeamKind.POLICE, town.police_units, POLICE_LAYOUT, "POL"),
                                    (TeamKind.FIRE, town.fire_units, FIRE_LAYOUT, "FIRE")):
        for i in range(n):
            loc = town.scale(*layout[i % len(layout)])
            out.append(ResponderTeam(id=f"{prefix}-{i + 1}", kind=kind, home=loc, location=loc))
    return out


# --- demand --------------------------------------------------------------------------------------


def _random_point(rng: np.random.Generator, town: TownProfile) -> tuple[float, float]:
    return town.to_latlon(float(rng.uniform(0, town.area_km)), float(rng.uniform(0, town.area_km)))


def _pick(rng: np.random.Generator, weights: dict) -> object:
    keys = list(weights)
    return keys[int(rng.choice(len(keys), p=np.array([weights[k] for k in keys])))]


def _needs(itype: IncidentType, sev: Severity, rng: np.random.Generator) -> PatientNeeds:
    C = Capability
    if sev == Severity.CRITICAL and itype in (IncidentType.VEHICLE_CRASH, IncidentType.BUS_CRASH,
                                              IncidentType.SHOOTING):
        or_need = 60 if rng.random() < OR_NEED_PROB else None
        return PatientNeeds(trauma_bay=True, trauma_surgeon=True, or_within_minutes=or_need,
                            er_bed=False, nurse=True, capability=C.TRAUMA_L2)
    if itype == IncidentType.MEDICAL_CARDIAC and sev == Severity.CRITICAL:
        return PatientNeeds(capability=C.CARDIAC_CATH)
    if itype == IncidentType.MEDICAL_STROKE and sev == Severity.CRITICAL:
        return PatientNeeds(capability=C.STROKE)
    return PatientNeeds(capability=C.GENERAL)


def _deterioration(sev: Severity, rng: np.random.Generator) -> float:
    return round(float(rng.uniform(0.0, 0.2)), 3) if sev == Severity.CRITICAL else 0.0


def _patient(pid: str, inc: str, itype: IncidentType, sev: Severity, call: int,
             rng: np.random.Generator) -> Patient:
    return Patient(id=pid, incident_id=inc, true_severity=sev, needs=_needs(itype, sev, rng),
                   deterioration_rate=_deterioration(sev, rng),
                   timestamps=PatientTimestamps(call=call))


def normal_stream(seed: int, town: TownProfile) -> tuple[list[Incident], list[Patient]]:
    arrivals = np.random.default_rng([seed, STREAM["arrivals"]])
    severity = np.random.default_rng([seed, STREAM["severity"]])
    scene = np.random.default_rng([seed, STREAM["scene"]])
    incidents, patients = [], []
    t = 0.0
    while True:
        t += float(arrivals.exponential(1 / town.calls_per_min))
        if t >= HORIZON:
            break
        itype = _pick(arrivals, NORMAL_MIX)
        loc = _random_point(arrivals, town)
        two = arrivals.random() < TWO_PATIENT_PROB.get(itype, DEFAULT_TWO_PATIENT_PROB)
        iid = f"I-{len(incidents) + 1:03d}"
        call = int(t)
        pids = []
        for k in range(2 if two else 1):
            sev = _pick(severity, SEVERITY_MIX[itype])
            p = _patient(f"{iid}-P{k}", iid, itype, sev, call, severity)
            patients.append(p)
            pids.append(p.id)
        extricate = itype == IncidentType.VEHICLE_CRASH and scene.random() < EXTRICATION_PROB
        incidents.append(Incident(
            id=iid, type=itype, location=loc, call_tick=call, reported_victims=len(pids),
            true_victim_ids=pids, needs_fire_extrication=bool(extricate),
            extrication_min=int(scene.integers(10, 21)) if extricate else 0,
        ))
    return incidents, patients


def mci_stream(seed: int, town: TownProfile) -> tuple[list[Incident], list[Patient]]:
    rng = np.random.default_rng([seed, STREAM["mci"]])
    scene = np.random.default_rng([seed, STREAM["mci_scene"]])
    incidents, patients = [], []

    # Shooting: 2 critical trauma victims, violent, unsecured until police secure it.
    sid, loc = "MCI-1", _random_point(rng, town)
    pids = []
    for k in range(2):
        p = _patient(f"{sid}-P{k}", sid, IncidentType.SHOOTING, Severity.CRITICAL,
                     SHOOTING_TICK, rng)
        patients.append(p)
        pids.append(p.id)
    incidents.append(Incident(
        id=sid, type=IncidentType.SHOOTING, location=loc, call_tick=SHOOTING_TICK,
        reported_victims=2, true_victim_ids=pids, violent=True, scene_secured=False,
        secure_delay_min=int(scene.integers(5, 16)),
    ))

    # Bus crash: ~31 victims with START-style severity mix.
    bid, loc = "MCI-2", _random_point(rng, town)
    n = int(rng.integers(BUS_VICTIMS[0], BUS_VICTIMS[1] + 1))
    shares = {s: float(rng.uniform(*r)) for s, r in BUS_MIX.items()}
    shares[Severity.MINOR] = 1.0 - sum(shares.values())
    order = [Severity.CRITICAL, Severity.SERIOUS, Severity.MINOR, Severity.EXPECTANT]
    counts = rng.multinomial(n, [shares[s] for s in order])
    sevs = [s for s, c in zip(order, counts, strict=True) for _ in range(int(c))]
    pids = []
    for k, sev in enumerate(sevs):
        p = _patient(f"{bid}-P{k:02d}", bid, IncidentType.BUS_CRASH, sev, BUS_CRASH_TICK, rng)
        patients.append(p)
        pids.append(p.id)
    incidents.append(Incident(
        id=bid, type=IncidentType.BUS_CRASH, location=loc, call_tick=BUS_CRASH_TICK,
        reported_victims=n, true_victim_ids=pids, needs_fire_extrication=True,
        extrication_min=int(scene.integers(15, 26)),
    ))
    return incidents, patients


def _walk_ins(seed: int, incidents: list[Incident], patients: dict[str, Patient],
              hosp: list[Hospital]) -> list[WalkIn]:
    rng = np.random.default_rng([seed, STREAM["walk_ins"]])
    out = []
    for inc in incidents:
        if inc.type not in (IncidentType.BUS_CRASH, IncidentType.SHOOTING):
            continue
        minors = sorted(p for p in inc.true_victim_ids
                        if patients[p].true_severity == Severity.MINOR)
        k = round(float(rng.uniform(*WALK_IN_SHARE)) * len(minors))
        if not k:
            continue
        nearest = min(hosp, key=lambda h: (haversine_km(h.location, inc.location), h.id))
        chosen = sorted(rng.choice(minors, size=k, replace=False).tolist())
        for pid in chosen:
            tick = inc.call_tick + int(rng.integers(WALK_IN_DELAY[0], WALK_IN_DELAY[1] + 1))
            out.append(WalkIn(patient_id=pid, hospital_id=nearest.id, tick=tick))
    return sorted(out, key=lambda w: (w.tick, w.patient_id))


_NARRATIVES = {
    IncidentType.MEDICAL_CARDIAC: ["My {who} grabbed his chest and collapsed, he's sweating a lot.",
                                   "Someone's having chest pain, they can barely breathe."],
    IncidentType.MEDICAL_STROKE: ["Her face is drooping and she can't lift her arm, please hurry.",
                                  "He's slurring his words and can't stand up."],
    IncidentType.MEDICAL_GENERAL: ["{Who} is really sick and dizzy, I don't know what's wrong.",
                                   "Someone fainted, they're awake now but confused."],
    IncidentType.FALL: ["An older person fell down the stairs and can't get up.",
                        "{Who} fell off a ladder, there's some blood."],
    IncidentType.VEHICLE_CRASH: ["Two cars hit each other, {count} hurt, one's stuck inside.",
                                 "There's been a crash at the intersection, {count} people hurt."],
    IncidentType.SHOOTING: ["Shots fired! I think {count} people are hit, the shooter ran off.",
                            "I heard gunshots, people are down, I'm hiding."],
    IncidentType.BUS_CRASH: ["A bus flipped over! There are so many people, maybe {count}, "
                             "people screaming.",
                             "Bus crash, lots of people hurt, maybe {count}, some can't move."],
}


def _narrative(inc: Incident, rng: np.random.Generator) -> str:
    templates = _NARRATIVES[inc.type]
    text = templates[int(rng.integers(len(templates)))]
    who = ["husband", "neighbor", "friend", "coworker"][int(rng.integers(4))]
    n = inc.reported_victims
    count = "one person" if n == 1 else f"{n}" if n < 10 else f"{n - n % 5} or so"
    return text.format(who=who, Who=f"My {who}", count=count)


def _incident_rng(seed: int, stream: str, incident_id: str) -> np.random.Generator:
    prefix, num = incident_id.split("-", 1)
    key = int(num) + (1000 if prefix == "MCI" else 0) if num.isdigit() else \
        2000 + sum(map(ord, num))
    return np.random.default_rng([seed, STREAM[stream], key])


def generate(seed: int, demand: str = "normal", population: int = DEFAULT_POPULATION) -> Scenario:
    if demand not in ("normal", "surge"):
        raise ValueError("demand must be 'normal' or 'surge'")
    town = TownProfile(population=population)
    hosp = hospitals(town)
    ambulances, firms = fleet(town, np.random.default_rng([seed, STREAM["busy_units"]]))
    occ = np.random.default_rng([seed, STREAM["occupancy"]])
    initial = {h.id: round(float(occ.uniform(0.5, 0.8)), 3) for h in hosp}
    initial_ward = {h.id: round(float(occ.uniform(*WARD_OCCUPANCY)), 3) for h in hosp}

    incidents, patients = normal_stream(seed, town)
    if demand == "surge":
        mci_inc, mci_pat = mci_stream(seed, town)
        incidents += mci_inc
        patients += mci_pat
    incidents.sort(key=lambda i: (i.call_tick, i.id))

    for inc in incidents:  # per-incident sub-streams: MCIs never shift normal-stream draws
        reported = _incident_rng(seed, "reported", inc.id)
        n = len(inc.true_victim_ids)
        inc.reported_victims = max(1, round(n * float(reported.uniform(0.8, 1.2))))
        inc.narrative = _narrative(inc, _incident_rng(seed, "narrative", inc.id))

    by_id = {p.id: p for p in patients}
    walk_ins = _walk_ins(seed, incidents, by_id, hosp)
    scenario = Scenario(
        seed=seed, demand=demand, horizon=HORIZON, drain_min=DRAIN, hospitals=hosp,
        initial_occupancy=initial, initial_ward_occupancy=initial_ward,
        population=population, town=town.summary(),
        ambulances=ambulances, firms=firms, teams=teams(town),
        incidents=incidents, patients=sorted(patients, key=lambda p: p.id), walk_ins=walk_ins,
    )
    validate_scenario(scenario)
    return scenario


# --- validation and I/O --------------------------------------------------------------------------


class ScenarioError(ValueError):
    pass


def validate_scenario(sc: Scenario) -> None:
    def check(cond: bool, msg: str) -> None:
        if not cond:
            raise ScenarioError(msg)

    ids = [h.id for h in sc.hospitals] + [a.id for a in sc.ambulances] + \
        [t.id for t in sc.teams] + [i.id for i in sc.incidents] + [p.id for p in sc.patients]
    check(len(ids) == len(set(ids)), "duplicate ids")
    patients = {p.id: p for p in sc.patients}
    hospital_ids = {h.id for h in sc.hospitals}
    for inc in sc.incidents:
        check(bool(inc.true_victim_ids), f"{inc.id} has no victims")
        check(0 <= inc.call_tick < sc.horizon, f"{inc.id} call outside horizon")
        for pid in inc.true_victim_ids:
            check(pid in patients and patients[pid].incident_id == inc.id,
                  f"{inc.id}: bad victim {pid}")
            check(patients[pid].timestamps.call == inc.call_tick, f"{pid}: call tick mismatch")
        check(not inc.violent or not inc.scene_secured, f"{inc.id}: violent scene starts secured")
    check(sum(len(i.true_victim_ids) for i in sc.incidents) == len(sc.patients),
          "patients not attached to exactly one incident")
    firm_units = {u for f in sc.firms for u in f.unit_ids}
    for amb in sc.ambulances:
        check(amb.state in (AmbulanceState.IDLE, AmbulanceState.RETURNING),
              f"{amb.id}: initial state must be IDLE or RETURNING")
        check(amb.state != AmbulanceState.RETURNING or amb.state_until_tick is not None,
              f"{amb.id}: RETURNING without state_until_tick")
        check((amb.owner == Owner.PRIVATE) == (amb.id in firm_units),
              f"{amb.id}: private units must belong to a firm")
    for w in sc.walk_ins:
        check(w.hospital_id in hospital_ids, f"walk-in to unknown hospital {w.hospital_id}")
        check(patients[w.patient_id].true_severity == Severity.MINOR, "walk-ins must be minor")
    for h in sc.hospitals:
        check(h.min_nurse_coverage <= h.nurses_total, f"{h.id}: coverage above staff")
        check(h.owner != Owner.PRIVATE or h.surge_contract is not None,
              f"{h.id}: private hospital without contract")


def scenario_path(seed: int, demand: str, out_dir: Path | None = None,
                  population: int = DEFAULT_POPULATION) -> Path:
    suffix = "" if population == DEFAULT_POPULATION else f"_p{population}"
    return (out_dir or DATA_DIR / "scenarios") / f"seed_{seed:02d}_{demand}{suffix}.json"


def to_json(sc: Scenario) -> str:
    return json.dumps(sc.model_dump(mode="json"), sort_keys=True, indent=1) + "\n"


def save(sc: Scenario, out_dir: Path | None = None) -> Path:
    path = scenario_path(sc.seed, sc.demand, out_dir, sc.population or DEFAULT_POPULATION)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_json(sc))
    return path


def load(path: str | Path) -> Scenario:
    sc = Scenario.model_validate_json(Path(path).read_text())
    validate_scenario(sc)
    return sc


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Generate a seeded ORCA-EMS scenario.")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--demand", choices=["normal", "surge"], default="normal")
    ap.add_argument("--population", type=int, default=DEFAULT_POPULATION)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    sc = generate(args.seed, args.demand, args.population)
    path = save(sc, args.out)
    sev = {s.value: sum(1 for p in sc.patients if p.true_severity == s) for s in Severity}
    print(f"wrote {path}: {len(sc.incidents)} incidents, {len(sc.patients)} patients {sev}, "
          f"{len(sc.walk_ins)} walk-ins")
    t = sc.town
    print(f"town: {t['population']:,} people on {t['area_km']:g}x{t['area_km']:g} km, "
          f"{t['calls_per_hour']} calls/h, {t['city_ambulances']} city + {t['private_units']} "
          f"private ambulances; ER beds {t['er_beds']}, ward beds {t['ward_beds']}, "
          f"surgical teams {t['surgical_teams']}, ED nurses {t['ed_nurses']}")


if __name__ == "__main__":
    main()
