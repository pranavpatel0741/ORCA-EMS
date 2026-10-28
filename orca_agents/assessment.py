"""Assessment agent: turns a call (and the first scene report) into a PriorityReport."""

from __future__ import annotations

from typing import Any

from orca_agents.llm_cache import AgentSpec
from orca_agents.models import PriorityReport
from orca_agents.tools import ASSESSMENT_TOOLS
from sim.observations import ObsIncident

SPEC = AgentSpec("assessment", "assessment.md", PriorityReport, tools=ASSESSMENT_TOOLS)


def payload(inc: ObsIncident) -> dict[str, Any]:
    report = None
    if inc.scene_reported:
        report = {}
        for p in inc.patients:
            key = (p.severity or "UNKNOWN").lower()
            report[key] = report.get(key, 0) + 1
    return {"call": {"id": inc.id, "type": inc.type, "reported_victims": inc.reported_victims,
                     "narrative": inc.narrative, "violent": inc.violent,
                     "trapped_victims": inc.needs_fire},
            "scene_report": report}
