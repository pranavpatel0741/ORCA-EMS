"""Confidence score for routing decisions (PLAN §14.5). Never uses the LLM's own confidence.

    score = 0.4 * consistency + 0.3 * margin + 0.2 * freshness + 0.1 * validator_clean

- consistency: currently defaults to 1.0; repeated allocator sampling is not implemented
- margin: objective gap between the chosen hospital and the best alternative (10 min = full)
- freshness: 1.0 for a current board, falling linearly to 0 at 30 minutes old
- validator_clean: 1.0 if the safety rules raised nothing for this unit last tick

The objective is severity-weighted time to definitive care: ETA plus a penalty when the board
says the hospital cannot take the patients now.
This is a routing heuristic, not a calibrated probability that the model is correct.
"""

from __future__ import annotations

from dataclasses import dataclass

import config.settings as settings
from baselines.nearest import can_treat
from baselines.rule_based import fits, projected_free
from sim.entities import Severity
from sim.observations import Observation, ObsPatient

WAIT_PENALTY_MIN = 30
WEIGHT = {
    Severity.CRITICAL: 3.0,
    Severity.SERIOUS: 2.0,
    Severity.MINOR: 1.0,
    Severity.EXPECTANT: 0.5,
}
FULL_MARGIN_MIN = 10.0


@dataclass
class Confidence:
    score: float
    consistency: float
    margin: float
    freshness: float
    validator_clean: float

    def decision(self) -> str:
        if self.score >= settings.CONFIDENCE_EXECUTE:
            return "execute"
        if self.score >= settings.CONFIDENCE_INFO_ROUND:
            return "info_round"
        return "escalate"


def objective(
    obs: Observation,
    unit_loc,
    hid: str,
    patients: list[ObsPatient],
    free: dict[str, int] | None = None,
) -> float:
    h = obs.hospitals[hid]
    weight = max((WEIGHT.get(p.severity or Severity.SERIOUS, 2.0) for p in patients), default=2.0)
    wait = (
        0
        if fits(free if free is not None else projected_free(obs, h), patients)
        else WAIT_PENALTY_MIN
    )
    return weight * (obs.eta(unit_loc, h.location) + wait)


def score(
    obs: Observation,
    unit_id: str,
    hid: str,
    patients: list[ObsPatient],
    *,
    consistency: float = 1.0,
    validator_clean: bool = True,
    live_free: dict[str, int] | None = None,
) -> Confidence:
    unit = obs.units[unit_id]
    w = settings.CONFIDENCE_WEIGHTS
    capable = [h for h in obs.hospitals if can_treat(obs.hospitals[h], patients, obs.surge_active)]
    chosen = objective(obs, unit.location, hid, patients, live_free)
    others = [objective(obs, unit.location, h, patients) for h in capable if h != hid]
    if not others:
        margin = 1.0
    else:
        gap = min(others) - chosen
        margin = max(0.0, min(1.0, gap / (FULL_MARGIN_MIN * WEIGHT[Severity.CRITICAL])))
    age = 0 if live_free is not None else obs.tick - obs.hospitals[hid].board_tick
    freshness = max(0.0, 1.0 - age / settings.FRESHNESS_ZERO_MIN)
    clean = 1.0 if validator_clean else 0.0
    total = (
        w["consistency"] * consistency
        + w["margin"] * margin
        + w["freshness"] * freshness
        + w["validator_clean"] * clean
    )
    return Confidence(round(total, 3), consistency, round(margin, 3), round(freshness, 3), clean)
