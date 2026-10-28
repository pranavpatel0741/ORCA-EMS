"""Read-only function tools for the agents (PLAN §14.2).

Every tool reads the `Observation` in the run context; none can change anything. Hospital
tools only return the calling hospital's own data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from agents import RunContextWrapper, function_tool

from sim.observations import Observation


@dataclass
class AgentContext:
    obs: Observation
    hospital_id: str | None = None  # set for hospital agents
    extra: dict[str, Any] = field(default_factory=dict)  # conflicts / offers for the allocator


def _dump(data: Any) -> str:
    return json.dumps(data, sort_keys=True, default=str)


def patient_brief(p) -> dict[str, Any]:
    needs = p.needs
    return {"id": p.id, "severity": p.severity,
            "needs": None if needs is None else {
                "capability": needs.capability, "trauma_bay": needs.trauma_bay,
                "surgeon": needs.trauma_surgeon, "or_within_min": needs.or_within_minutes}}


@function_tool
def get_incident(ctx: RunContextWrapper[AgentContext], incident_id: str) -> str:
    """Observed details of one active call: type, caller report, known patients."""
    inc = ctx.context.obs.incidents.get(incident_id)
    if inc is None:
        return _dump({"error": f"no active call {incident_id}"})
    return _dump({"id": inc.id, "type": inc.type, "reported_victims": inc.reported_victims,
                  "narrative": inc.narrative, "violent": inc.violent, "secured": inc.secured,
                  "needs_fire": inc.needs_fire, "scene_reported": inc.scene_reported,
                  "patients": [patient_brief(p) | {"status": p.status} for p in inc.patients]})


@function_tool
def get_scene_reports(ctx: RunContextWrapper[AgentContext]) -> str:
    """Counts by observed severity for every call a crew has reported from."""
    out = {}
    for inc in ctx.context.obs.incidents.values():
        if inc.scene_reported:
            counts: dict[str, int] = {}
            for p in inc.patients:
                counts[p.severity or "UNKNOWN"] = counts.get(p.severity or "UNKNOWN", 0) + 1
            out[inc.id] = counts
    return _dump(out)


@function_tool
def get_available_units(ctx: RunContextWrapper[AgentContext]) -> str:
    """Ambulances that are free to send now."""
    return _dump([{"id": u.id, "type": u.unit_type, "state": u.state}
                  for u in ctx.context.obs.free_units()])


@function_tool
def estimate_eta(ctx: RunContextWrapper[AgentContext], unit_id: str, destination_id: str) -> str:
    """Median and 90th-percentile driving minutes from a unit to a call or hospital ID."""
    obs = ctx.context.obs
    unit = obs.units.get(unit_id)
    dest = obs.hospitals.get(destination_id) or obs.incidents.get(destination_id)
    if unit is None or dest is None:
        return _dump({"error": "unknown unit or destination"})
    return _dump({"median_min": obs.eta(unit.location, dest.location),
                  "p90_min": obs.eta_p90(unit.location, dest.location)})


@function_tool
def get_priority_queue(ctx: RunContextWrapper[AgentContext]) -> str:
    """Known patients waiting on scene with no ambulance, most severe first."""
    order = {"CRITICAL": 0, "SERIOUS": 1, "MINOR": 2, "EXPECTANT": 3, None: 1}
    obs = ctx.context.obs
    rows = [patient_brief(p) | {"call": inc.id}
            for inc in obs.incidents.values() for p in obs.waiting(inc.id)]
    return _dump(sorted(rows, key=lambda r: (order.get(r["severity"], 1), r["id"])))


@function_tool
def get_hospital_board(ctx: RunContextWrapper[AgentContext]) -> str:
    """The shared hospital status board (may be up to 15 minutes old)."""
    obs = ctx.context.obs
    return _dump([{"id": h.id, "capabilities": h.capabilities, "owner": h.owner,
                   "contract": h.contract, "free": h.free, "queue": h.queue,
                   "boarding": h.boarding, "board_age_min": obs.tick - h.board_tick}
                  for h in obs.hospitals.values()])


@function_tool
def get_my_status(ctx: RunContextWrapper[AgentContext]) -> str:
    """This hospital's live status (beds, bays, surgeons, ORs, nurses, queue)."""
    hid = ctx.context.hospital_id
    return _dump(ctx.context.obs.own_status.get(hid or "", {"error": "not a hospital agent"}))


@function_tool
def get_my_staff(ctx: RunContextWrapper[AgentContext]) -> str:
    """This hospital's nurses on duty, minimum coverage, and loans."""
    s = ctx.context.obs.own_status.get(ctx.context.hospital_id or "", {})
    return _dump({k: s.get(k) for k in ("nurses_on_duty", "min_nurse_coverage",
                                        "nurses_loaned_in", "nurses_loaned_out")})


@function_tool
def get_my_incoming(ctx: RunContextWrapper[AgentContext]) -> str:
    """Patients already on their way to this hospital."""
    obs = ctx.context.obs
    return _dump([patient_brief(p) for p in obs.incoming(ctx.context.hospital_id or "")])


@function_tool
def get_pending_conflicts(ctx: RunContextWrapper[AgentContext]) -> str:
    """Conflicting or unresolved proposals the allocator must settle."""
    return _dump(ctx.context.extra.get("conflicts", []))


@function_tool
def get_offers(ctx: RunContextWrapper[AgentContext]) -> str:
    """Every hospital's latest answer (accept / counter / reject) in this negotiation."""
    return _dump(ctx.context.extra.get("offers", []))


ASSESSMENT_TOOLS = (get_incident, get_scene_reports)
DISPATCH_TOOLS = (get_available_units, estimate_eta, get_priority_queue, get_hospital_board)
HOSPITAL_TOOLS = (get_my_status, get_my_staff, get_my_incoming)
ALLOCATOR_TOOLS = (get_pending_conflicts, get_offers, estimate_eta)
