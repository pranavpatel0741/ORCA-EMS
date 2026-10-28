"""Dispatch agent: assigns units to calls and chooses hospitals for loaded units."""

from __future__ import annotations

from typing import Any

from orca_agents.llm_cache import AgentSpec
from orca_agents.models import DispatchPlan, PriorityReport
from orca_agents.tools import DISPATCH_TOOLS, patient_brief
from sim.observations import Observation

SPEC = AgentSpec("dispatch", "dispatch.md", DispatchPlan, tools=DISPATCH_TOOLS)


def hospital_rows(obs: Observation) -> list[dict[str, Any]]:
    return [{"id": h.id, "capabilities": h.capabilities, "owner": h.owner,
             "stabilization_only": h.stabilization_only, "contract": h.contract,
             "free": {k: h.free[k] for k in ("er_bed", "trauma_bay", "surgeon", "or",
                                             "ward_bed", "nurse_slot")},
             "queue": h.queue, "boarding": h.boarding, "board_age_min": obs.tick - h.board_tick,
             "already_sent": len(obs.incoming(h.id))}
            for h in obs.hospitals.values()]


def payload(obs: Observation, reports: dict[str, PriorityReport],
            feedback: list[dict[str, Any]], focus_units: set[str] | None = None) -> dict:
    """Compact decision input. `focus_units` limits routing to units being renegotiated."""
    calls = []
    for inc in sorted(obs.incidents.values(), key=lambda i: (i.call_tick, i.id)):
        waiting = obs.waiting(inc.id)
        unknown = 0 if inc.patients else obs.unassigned_victims(inc.id)
        if not waiting and not unknown:
            continue
        rep = reports.get(inc.id)
        calls.append({"id": inc.id, "type": inc.type, "called_min": inc.call_tick,
                      "urgency": rep.urgency if rep else None,
                      "mode": rep.mode if rep else None,
                      "waiting_patients": [patient_brief(p) for p in waiting],
                      "victims_not_yet_seen": unknown,
                      "unsafe_scene": inc.violent and not inc.secured})
    free = obs.free_units()
    busy = [u for u in obs.units.values() if u.state in ("EN_ROUTE", "STAGING")
            and u.reassignable and not u.patient_ids]
    loaded = [u for u in obs.units_needing_destination()
              if focus_units is None or u.id in focus_units]
    return {
        "minute": obs.tick, "information": obs.info, "surge_active": obs.surge_active,
        "calls": calls,
        "free_units": [{"id": u.id, "type": u.unit_type,
                        "eta_to_calls_min": {c["id"]: obs.eta(u.location,
                                                             obs.incidents[c["id"]].location)
                                             for c in calls}} for u in free],
        "en_route_units": [{"id": u.id, "going_to": u.assigned_incident} for u in busy],
        "loaded_units": [{"id": u.id,
                          "patients": [patient_brief(p) for pid in u.patient_ids
                                       if (p := obs.patient(pid))],
                          "eta_to_hospitals_min": {h.id: obs.eta(u.location, h.location)
                                                   for h in obs.hospitals.values()}}
                         for u in loaded],
        "hospitals": hospital_rows(obs),
        "private_firms": [{"id": f.id, "units_left": min(f.max_units, len(f.unit_ids))
                           - f.in_use} for f in obs.firms.values()],
        "feedback": feedback,
    }
