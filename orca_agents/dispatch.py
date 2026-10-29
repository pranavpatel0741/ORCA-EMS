"""Dispatch agent: assigns units to calls and chooses hospitals for loaded units."""

from __future__ import annotations

from typing import Any

from orca_agents.llm_cache import AgentSpec
from orca_agents.models import DispatchPlan, PriorityReport
from orca_agents.tools import DISPATCH_TOOLS, patient_brief
from sim.observations import Observation

SEVERITY_ORDER = {"CRITICAL": 0, "SERIOUS": 1, "MINOR": 2, "EXPECTANT": 3}
SPEC = AgentSpec("dispatch", "dispatch.md", DispatchPlan, tools=DISPATCH_TOOLS)


def hospital_rows(obs: Observation) -> list[dict[str, Any]]:
    """The status board plus a few derived facts, stated plainly so the model does not have to
    work them out (the baselines compute the same facts from the same board)."""
    rows = []
    for h in obs.hospitals.values():
        sent = len(obs.incoming(h.id))
        trauma = bool({"TRAUMA_L1", "TRAUMA_L2"} & set(h.capabilities)) and \
            h.totals.get("surgeon", 0) > 0
        if h.owner == "PRIVATE":
            takes = ("now: stable SERIOUS non-trauma patients only" if obs.surge_active
                     else "no: only during a mass-casualty surge")
        else:
            takes = "yes"
        rows.append({
            "id": h.id, "capabilities": h.capabilities, "owner": h.owner,
            "trauma_center": trauma, "stabilization_only": h.stabilization_only,
            "takes_ambulance_patients": takes, "contract": h.contract,
            "free": {k: h.free[k] for k in ("er_bed", "trauma_bay", "surgeon", "or",
                                            "ward_bed", "nurse_slot")},
            "already_sent": sent,
            "er_beds_left_after_ambulances_on_the_way": h.free["er_bed"] - sent,
            "queue": h.queue, "boarding": h.boarding, "board_age_min": obs.tick - h.board_tick})
    return rows


def payload(obs: Observation, reports: dict[str, PriorityReport],
            feedback: list[dict[str, Any]], focus_units: set[str] | None = None) -> dict:
    """Compact decision input. `focus_units` limits routing to units being renegotiated."""
    calls = []
    for inc in sorted(obs.incidents.values(), key=lambda i: (i.call_tick, i.id)):
        # Crews already sent with no patient list load waiting patients themselves on scene
        # (most severe first), so those patients are not offered to Dispatch again.
        crews = [u for u in obs.units.values() if u.assigned_incident == inc.id
                 and not u.patient_ids and u.state in ("EN_ROUTE", "STAGING", "ON_SCENE")]
        waiting = sorted(obs.waiting(inc.id), key=lambda p: SEVERITY_ORDER.get(p.severity, 1))
        critical = any(p.severity == "CRITICAL" for p in waiting)
        covered = sum(1 if critical else 2 for _ in crews)
        waiting = waiting[covered:]
        unknown = 0 if inc.patients else max(0, obs.unassigned_victims(inc.id))
        if not waiting and not unknown:
            continue
        rep = reports.get(inc.id)
        calls.append({"id": inc.id, "type": inc.type, "called_min": inc.call_tick,
                      "urgency": rep.urgency if rep else None,
                      "mode": rep.mode if rep else None,
                      "waiting_patients": [patient_brief(p) for p in waiting],
                      "victims_not_yet_seen": unknown,
                      "crews_already_assigned": [{"id": u.id, "state": u.state} for u in crews],
                      "unsafe_scene": inc.violent and not inc.secured})
    free = obs.free_units()
    busy = [u for u in obs.units.values() if u.state in ("EN_ROUTE", "STAGING")
            and u.reassignable and not u.patient_ids]
    loaded = [u for u in obs.units_needing_destination()
              if focus_units is None or u.id in focus_units]
    return {
        "minute": obs.tick, "information": obs.info, "surge_active": obs.surge_active,
        "calls": calls,
        "free_unit_count": len(free),
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
