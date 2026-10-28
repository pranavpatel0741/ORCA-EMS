"""Reference baseline: what often happens today (PLAN §15 M5).

- Calls are served first-come, first-served.
- Each waiting patient group gets the nearest free unit (critical patients travel alone,
  otherwise up to two non-critical patients per unit, per R7). Before the scene report the
  victims are unknown, so units are sent for the caller's estimate and the crew triages.
- Each loaded unit goes to the nearest hospital that can treat its patients, ignoring how
  crowded it is. If the safety rules reject that hospital, the next nearest is tried.
- No mutual aid, no staff loans, no negotiation.

It sees only the `Observation`, like every other policy.
"""

from __future__ import annotations

import math

from sim.actions import Action, Dispatch, RouteToHospital
from sim.entities import Severity
from sim.hospital import SEVERITY_PRIORITY, resource_demand
from sim.observations import Observation, ObsHospital, ObsPatient, ObsUnit
from sim.validator import has_capability


def can_treat(h: ObsHospital, patients: list[ObsPatient], surge_active: bool) -> bool:
    """Structural check from public hospital information (capabilities, contract)."""
    for p in patients:
        sev = p.severity or Severity.SERIOUS
        needs = p.needs
        if needs is None:
            continue
        trauma = needs.trauma_bay
        if trauma and h.stabilization_only:
            return False
        if not has_capability(set(h.capabilities), needs.capability):
            return False
        demand = resource_demand(needs, sev)
        if any(h.totals.get(r, 0) <= 0 for r, n in demand.items() if n > 0):
            return False
        if h.owner == "PRIVATE":
            c = h.contract or {}
            if not surge_active or sev not in c.get("eligible_severities", []):
                return False
            if trauma and not c.get("accepts_critical_trauma"):
                return False
    return True


def patient_groups(waiting: list[ObsPatient]) -> list[list[ObsPatient]]:
    """R7 grouping: critical patients alone, others in pairs; most severe first."""
    order = sorted(waiting, key=lambda p: (SEVERITY_PRIORITY[p.severity or Severity.SERIOUS],
                                           p.id))
    groups, rest = [], []
    for p in order:
        if p.severity == Severity.CRITICAL:
            groups.append([p])
        else:
            rest.append(p)
    groups += [rest[i:i + 2] for i in range(0, len(rest), 2)]
    return groups


class NearestPolicy:
    name = "nearest"

    def __init__(self) -> None:
        self._rejected: dict[str, set[str]] = {}  # unit -> hospitals the rules rejected

    def _note_rejections(self, obs: Observation) -> None:
        for r in obs.rejections:
            if r.action.get("kind") == "route":
                self._rejected.setdefault(r.action["unit_id"], set()).add(r.action["hospital_id"])
        needing = {u.id for u in obs.units_needing_destination()}
        self._rejected = {u: hs for u, hs in self._rejected.items() if u in needing}

    def dispatch(self, obs: Observation) -> list[Action]:
        actions: list[Action] = []
        free = {u.id: u for u in obs.free_units()}
        for inc in sorted(obs.incidents.values(), key=lambda i: (i.call_tick, i.id)):
            if inc.patients:
                groups = [[p.id for p in g] for g in patient_groups(obs.waiting(inc.id))]
            else:  # victims unknown until the scene report: send for the estimate
                groups = [[] for _ in range(math.ceil(obs.unassigned_victims(inc.id) / 2))]
            for group in groups:
                if not free:
                    return actions
                unit = min(free.values(), key=lambda u: (obs.eta(u.location, inc.location), u.id))
                del free[unit.id]
                actions.append(Dispatch(unit_id=unit.id, incident_id=inc.id, patient_ids=group,
                                        rationale="nearest free unit"))
        return actions

    def choose_hospital(self, obs: Observation, unit: ObsUnit) -> str | None:
        patients = [p for pid in unit.patient_ids if (p := obs.patient(pid))]
        rejected = self._rejected.get(unit.id, set())
        ranked = sorted(obs.hospitals.values(),
                        key=lambda h: (obs.eta(unit.location, h.location), h.id))
        capable = [h.id for h in ranked if can_treat(h, patients, obs.surge_active)]
        for hid in capable:
            if hid not in rejected:
                return hid
        self._rejected.pop(unit.id, None)  # everything was rejected once: start over
        return capable[0] if capable else (ranked[0].id if ranked else None)

    def route(self, obs: Observation) -> list[Action]:
        actions: list[Action] = []
        for unit in sorted(obs.units_needing_destination(), key=lambda u: u.id):
            hid = self.choose_hospital(obs, unit)
            if hid:
                actions.append(RouteToHospital(unit_id=unit.id, hospital_id=hid,
                                               rationale="nearest hospital that can treat"))
        return actions

    def decide(self, obs: Observation) -> list[Action]:
        self._note_rejections(obs)
        return self.dispatch(obs) + self.route(obs)
