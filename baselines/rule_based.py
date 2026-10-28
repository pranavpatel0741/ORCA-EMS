"""Strong deterministic baseline (PLAN §15 M5). Same observations and ETA model as the agents.

- Severity-priority queue across all calls (critical first, then by call time). Before a scene
  report, a mass-casualty call counts as critical-priority work for its estimated victims.
- Each patient group gets the nearest free unit.
- Mutual aid is requested when known critical patients waiting outnumber free units.
- Routing: the nearest hospital that can treat the patients *and* is projected to have the
  needed resources (status board free capacity minus patients this dispatcher already sent
  there). Non-critical patients are spread: among capable hospitals with space whose ETA is
  within 10 minutes of the nearest, pick the one with the most free ER beds.
- If no hospital is projected to have space, the nearest capable one is used (the patient will
  queue). Hospitals the safety rules rejected for a unit are skipped on the next try.
"""

from __future__ import annotations

import math

from baselines.nearest import NearestPolicy, can_treat, patient_groups
from sim.actions import Action, ActivateMutualAid, Dispatch
from sim.entities import Severity
from sim.hospital import SEVERITY_PRIORITY, resource_demand
from sim.observations import Observation, ObsHospital, ObsPatient, ObsUnit

SPREAD_WINDOW_MIN = 10
MCI_TYPES = {"BUS_CRASH", "SHOOTING"}
EXPECTED_CRITICAL_SHARE = 0.2  # used only before a scene report, for mutual-aid sizing


def projected_free(obs: Observation, h: ObsHospital) -> dict[str, int]:
    free = dict(h.free)
    free["er_bed"] -= h.queue
    for p in obs.incoming(h.id):
        if p.needs is None:
            continue
        for r, n in resource_demand(p.needs, p.severity or Severity.SERIOUS).items():
            free[r] = free.get(r, 0) - n
    return free


def fits(free: dict[str, int], patients: list[ObsPatient]) -> bool:
    need: dict[str, int] = {}
    for p in patients:
        if p.needs is None:
            continue
        for r, n in resource_demand(p.needs, p.severity or Severity.SERIOUS).items():
            need[r] = need.get(r, 0) + n
    return all(free.get(r, 0) >= n for r, n in need.items() if n > 0)


class RuleBasedPolicy(NearestPolicy):
    name = "rule_based"

    def _priority_groups(self, obs: Observation) -> list[tuple[tuple, str, list[str]]]:
        out = []
        for inc in obs.incidents.values():
            if inc.patients:
                for g in patient_groups(obs.waiting(inc.id)):
                    sev = min(SEVERITY_PRIORITY[p.severity or Severity.SERIOUS] for p in g)
                    out.append(((sev, inc.call_tick, inc.id, g[0].id), inc.id, [p.id for p in g]))
            else:
                sev = 0 if inc.type in MCI_TYPES or inc.violent else 1
                for k in range(math.ceil(obs.unassigned_victims(inc.id) / 2)):
                    out.append(((sev, inc.call_tick, inc.id, f"~{k}"), inc.id, []))
        return sorted(out)

    def dispatch(self, obs: Observation) -> list[Action]:
        actions: list[Action] = []
        free = {u.id: u for u in obs.free_units()}
        for _, inc_id, group in self._priority_groups(obs):
            if not free:
                break
            loc = obs.incidents[inc_id].location
            unit = min(free.values(), key=lambda u: (obs.eta(u.location, loc), u.id))
            del free[unit.id]
            actions.append(Dispatch(unit_id=unit.id, incident_id=inc_id, patient_ids=group,
                                    rationale="highest-priority patients, nearest free unit"))
        return actions

    def mutual_aid(self, obs: Observation, dispatched: int) -> list[Action]:
        critical = sum(1 for inc in obs.incidents.values() for p in obs.waiting(inc.id)
                       if p.severity == Severity.CRITICAL)
        critical += sum(round(inc.reported_victims * EXPECTED_CRITICAL_SHARE)
                        for inc in obs.incidents.values()
                        if not inc.patients and inc.type in MCI_TYPES)
        shortfall = critical - (len(obs.free_units()) - dispatched)
        actions: list[Action] = []
        for firm in sorted(obs.firms.values(), key=lambda f: f.id):
            room = min(firm.max_units, len(firm.unit_ids)) - firm.in_use
            if shortfall > 0 and room > 0:
                n = min(room, shortfall)
                actions.append(ActivateMutualAid(firm_id=firm.id, units=n,
                                                 rationale=f"{critical} critical patients "
                                                           "waiting, not enough free units"))
                shortfall -= n
        return actions

    def choose_hospital(self, obs: Observation, unit: ObsUnit) -> str | None:
        patients = [p for pid in unit.patient_ids if (p := obs.patient(pid))]
        rejected = self._rejected.get(unit.id, set())
        ranked = sorted((h for h in obs.hospitals.values()
                         if can_treat(h, patients, obs.surge_active) and h.id not in rejected),
                        key=lambda h: (obs.eta(unit.location, h.location), h.id))
        if not ranked:
            return super().choose_hospital(obs, unit)
        with_space = [h for h in ranked if fits(projected_free(obs, h), patients)]
        critical = any(p.severity == Severity.CRITICAL for p in patients)
        if not with_space:
            return ranked[0].id
        if critical:
            return with_space[0].id
        nearest = obs.eta(unit.location, ranked[0].location)
        window = [h for h in with_space
                  if obs.eta(unit.location, h.location) <= nearest + SPREAD_WINDOW_MIN]
        if not window:
            return with_space[0].id
        return max(window, key=lambda h: (projected_free(obs, h).get("er_bed", 0),
                                          -obs.eta(unit.location, h.location), h.id)).id

    def decide(self, obs: Observation) -> list[Action]:
        self._note_rejections(obs)
        dispatches = self.dispatch(obs)
        return dispatches + self.mutual_aid(obs, len(dispatches)) + self.route(obs)
