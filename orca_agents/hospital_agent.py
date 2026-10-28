"""Hospital agents (one per hospital): answer admission proposals and staff requests."""

from __future__ import annotations

from typing import Any

from orca_agents.llm_cache import AgentSpec
from orca_agents.models import AdmissionDecision, StaffDecision
from orca_agents.tools import HOSPITAL_TOOLS, patient_brief
from sim.observations import Observation


def hospital_type(obs: Observation, hid: str) -> str:
    h = obs.hospitals[hid]
    if h.owner == "PRIVATE":
        return "private hospital with a surge contract"
    if h.stabilization_only:
        return "community hospital with a stabilization-only trauma bay"
    if "TRAUMA_L1" in h.capabilities:
        return "level 1 trauma center"
    if "TRAUMA_L2" in h.capabilities:
        return "level 2 trauma center"
    return "community hospital"


def spec(obs: Observation, hid: str, staff: bool = False) -> AgentSpec:
    return AgentSpec(f"hospital:{hid}", "hospital.md", StaffDecision if staff else
                     AdmissionDecision,
                     prompt_vars=(("hospital_name", f"Hospital {hid}"),
                                  ("hospital_type", hospital_type(obs, hid))),
                     tools=HOSPITAL_TOOLS)


def _status(obs: Observation, hid: str) -> dict[str, Any]:
    s = obs.own_status[hid]
    return {"free": s["free"], "queue_scenario": s["queue_scenario"], "boarding": s["boarding"],
            "ambulances_at_door": s["ambulances_waiting"], "er_occupancy": s["er_occupancy"],
            "nurses_on_duty": s["nurses_on_duty"],
            "min_nurse_coverage": s["min_nurse_coverage"],
            "contract": obs.hospitals[hid].contract, "surge_active": obs.surge_active,
            "capabilities": obs.hospitals[hid].capabilities,
            "stabilization_only": obs.hospitals[hid].stabilization_only}


def admission_payload(obs: Observation, hid: str,
                      proposals: list[dict[str, Any]]) -> dict[str, Any]:
    return {"hospital": hid, "minute": obs.tick, "my_status": _status(obs, hid),
            "already_incoming": [patient_brief(p) for p in obs.incoming(hid)],
            "proposals": proposals}


def staff_payload(obs: Observation, hid: str, requester: str, nurses: int,
                  why: str) -> dict[str, Any]:
    return {"hospital": hid, "minute": obs.tick, "my_status": _status(obs, hid),
            "request": {"from": f"Hospital {requester}", "nurses": nurses, "why": why}}
