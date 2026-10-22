"""Reference baseline: what often happens today (PLAN §15 M5).

- Calls are served first-come, first-served.
- Each waiting patient group gets the nearest free unit (critical patients travel alone,
  otherwise up to two non-critical patients per unit, per R7).
- Each loaded unit goes to the nearest hospital the validator accepts, ignoring how crowded it
  is beyond what the hard rules forbid.
- No mutual aid, no staff loans, no negotiation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sim.actions import Action, Dispatch, RouteToHospital
from sim.entities import AmbulanceState, Severity
from sim.hospital import SEVERITY_PRIORITY
from sim.state_machine import can_reassign
from sim.travel import haversine_km

if TYPE_CHECKING:
    from sim.engine import Engine


class NearestPolicy:
    name = "nearest"

    def decide(self, engine: Engine) -> list[Action]:
        actions: list[Action] = []
        used: set[str] = set()
        incidents = sorted(engine.active_incidents.values(), key=lambda i: (i.call_tick, i.id))
        for inc in incidents:
            waiting = sorted(
                (p for p in engine.waiting_patients(inc.id) if p.ambulance_id is None),
                key=lambda p: (SEVERITY_PRIORITY[p.true_severity], p.id),
            )
            while waiting:
                free = [a for a in engine.ambulances.values()
                        if a.id not in used and a.state in (AmbulanceState.IDLE,
                                                            AmbulanceState.RETURNING)
                        and can_reassign(a) and engine.unit_available(a.id)]
                if not free:
                    break
                unit = min(free, key=lambda a: (haversine_km(engine.position(a.id),
                                                             inc.location), a.id))
                if waiting[0].true_severity == Severity.CRITICAL:
                    group = [waiting.pop(0)]
                else:
                    group = [p for p in waiting if p.true_severity != Severity.CRITICAL][:2]
                    waiting = [p for p in waiting if p not in group]
                used.add(unit.id)
                actions.append(Dispatch(unit_id=unit.id, incident_id=inc.id,
                                        patient_ids=[p.id for p in group],
                                        rationale="nearest free unit"))
        for amb in sorted(engine.units_needing_destination(), key=lambda a: a.id):
            by_distance = sorted(engine.hospitals, key=lambda h: (
                haversine_km(engine.position(amb.id), engine.hospitals[h].config.location), h))
            for hid in by_distance:
                route = RouteToHospital(unit_id=amb.id, hospital_id=hid,
                                        rationale="nearest acceptable hospital")
                if all(r.ok for r in engine.validator.check(route, engine)):
                    actions.append(route)
                    break
        return actions
