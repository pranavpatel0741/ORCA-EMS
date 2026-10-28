"""Allocator agent: settles conflicts and negotiations that did not converge."""

from __future__ import annotations

from typing import Any

from orca_agents.dispatch import hospital_rows
from orca_agents.llm_cache import AgentSpec
from orca_agents.models import Resolution
from orca_agents.tools import ALLOCATOR_TOOLS, patient_brief
from sim.observations import Observation

SPEC = AgentSpec("allocator", "allocator.md", Resolution, tools=ALLOCATOR_TOOLS)


def payload(obs: Observation, conflicts: list[dict[str, Any]],
            offers: list[dict[str, Any]]) -> dict[str, Any]:
    units = sorted({c["unit_id"] for c in conflicts if c.get("unit_id")})
    return {
        "minute": obs.tick,
        "conflicts": conflicts,
        "offers": offers,
        "units": [{"id": uid, "state": obs.units[uid].state,
                   "patients": [patient_brief(p) for pid in obs.units[uid].patient_ids
                                if (p := obs.patient(pid))],
                   "eta_to_hospitals_min": {h.id: obs.eta(obs.units[uid].location, h.location)
                                            for h in obs.hospitals.values()}}
                  for uid in units if uid in obs.units],
        "hospitals": hospital_rows(obs),
    }
