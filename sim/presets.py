"""Ready-made incidents for the dashboard, in the fixed default town.

Each preset reuses the generator's town, hospitals, fleet, teams, and starting hospital load;
only the incidents differ. Single-incident presets call at minute 2 so the action starts at once.
The experiment grid keeps using `sim.generator.generate`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from sim.entities import Incident, IncidentType, Patient, Scenario, Severity
from sim.generator import (
    DEFAULT_POPULATION,
    STREAM,
    WARD_OCCUPANCY,
    _narrative,
    _patient,
    _walk_ins,
    fleet,
    generate,
    hospitals,
    mci_stream,
    teams,
    validate_scenario,
)
from sim.town import TownProfile

START_TICK = 2
PRESET_STREAM = 40


@dataclass(frozen=True)
class Preset:
    name: str
    description: str
    horizon: int  # minutes in which calls can arrive
    drain: int  # extra minutes simulated afterwards
    build: Callable[[int, TownProfile], tuple[list[Incident], list[Patient]]]


def _call(iid: str, itype: IncidentType, loc: tuple[float, float], sevs: list[Severity],
          seed: int, **extra) -> tuple[list[Incident], list[Patient]]:
    rng = np.random.default_rng([seed, PRESET_STREAM, sum(map(ord, iid))])
    patients = [_patient(f"{iid}-P{k}", iid, itype, sev, START_TICK, rng)
                for k, sev in enumerate(sevs)]
    inc = Incident(id=iid, type=itype, location=loc, call_tick=START_TICK,
                   reported_victims=len(patients), true_victim_ids=[p.id for p in patients],
                   **extra)
    inc.narrative = _narrative(inc, rng)
    return [inc], patients


def _cardiac(seed: int, town: TownProfile):
    # South-west corner: the nearest hospital (D) has no cath lab, A and C are farther away.
    return _call("I-CARDIAC", IncidentType.MEDICAL_CARDIAC, town.to_latlon(4, 3),
                 [Severity.CRITICAL], seed)


def _car_crash(seed: int, town: TownProfile):
    return _call("I-CRASH", IncidentType.VEHICLE_CRASH, town.to_latlon(16, 15),
                 [Severity.CRITICAL, Severity.SERIOUS, Severity.MINOR], seed,
                 needs_fire_extrication=True, extrication_min=15)


def _shift(incidents: list[Incident], patients: list[Patient]) -> None:
    for inc in incidents:
        inc.call_tick = START_TICK
    for p in patients:
        p.timestamps.call = START_TICK


def _shooting(seed: int, town: TownProfile):
    incidents, patients = mci_stream(seed, town)
    keep = [i for i in incidents if i.type == IncidentType.SHOOTING]
    pats = [p for p in patients if p.incident_id in {i.id for i in keep}]
    _shift(keep, pats)
    return keep, pats


def _bus_crash(seed: int, town: TownProfile):
    incidents, patients = mci_stream(seed, town)
    keep = [i for i in incidents if i.type == IncidentType.BUS_CRASH]
    pats = [p for p in patients if p.incident_id in {i.id for i in keep}]
    _shift(keep, pats)
    return keep, pats


PRESETS: dict[str, Preset] = {p.name: p for p in [
    Preset("Cardiac arrest", "One critical cardiac patient in the south-west; the nearest "
           "hospital has no cath lab.", 30, 90, _cardiac),
    Preset("Two-car crash", "Three victims (1 critical, 1 serious, 1 minor); the driver is "
           "trapped until fire crews cut them out.", 30, 120, _car_crash),
    Preset("Shooting", "Two critical victims; ambulances must stage until police secure the "
           "scene.", 30, 120, _shooting),
    Preset("School bus crash", "About 30 victims at once; walk-in patients flood the nearest "
           "hospital.", 30, 240, _bus_crash),
    Preset("Bus crash + shooting", "Both mass-casualty incidents during a normal afternoon of "
           "911 calls.", 180, 120, lambda s, t: ([], [])),
    Preset("Normal day", "Three hours of routine 911 calls in a town of 50,000.", 180, 120,
           lambda s, t: ([], [])),
]}


def build_preset(name: str, seed: int = 7, population: int = DEFAULT_POPULATION) -> Scenario:
    preset = PRESETS[name]
    if name == "Bus crash + shooting":
        return generate(seed, "surge", population)
    if name == "Normal day":
        return generate(seed, "normal", population)
    town = TownProfile(population=population)
    hosp = hospitals(town)
    ambulances, firms = fleet(town, np.random.default_rng([seed, STREAM["busy_units"]]))
    occ = np.random.default_rng([seed, STREAM["occupancy"]])
    initial = {h.id: round(float(occ.uniform(0.5, 0.8)), 3) for h in hosp}
    initial_ward = {h.id: round(float(occ.uniform(*WARD_OCCUPANCY)), 3) for h in hosp}
    incidents, patients = preset.build(seed, town)
    walk_ins = _walk_ins(seed, incidents, {p.id: p for p in patients}, hosp)
    scenario = Scenario(
        seed=seed, demand=name, horizon=preset.horizon, drain_min=preset.drain, hospitals=hosp,
        initial_occupancy=initial, initial_ward_occupancy=initial_ward, population=population,
        town=town.summary(), ambulances=ambulances, firms=firms, teams=teams(town),
        incidents=incidents, patients=sorted(patients, key=lambda p: p.id), walk_ins=walk_ins,
    )
    validate_scenario(scenario)
    return scenario
