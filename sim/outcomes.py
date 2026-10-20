"""Synthetic outcome model (PLAN §16). NOT clinically validated.

Survival probability decays logistically with time to definitive care:
    p(t) = p0 / (1 + exp(k * (1 + deterioration_rate) * (t - t50)))
Untreated patients whose probability falls below `DEATH_THRESHOLD` are marked DECEASED.
Once a patient reaches definitive care, their probability is frozen.
"""

from __future__ import annotations

import math

from pydantic import BaseModel

from sim.entities import Severity


class OutcomeParams(BaseModel):
    p0: float
    t50: float  # minutes at which survival is halved
    k: float  # steepness per minute


OUTCOME_PARAMS: dict[Severity, OutcomeParams] = {
    Severity.CRITICAL: OutcomeParams(p0=0.95, t50=90.0, k=0.05),
    Severity.SERIOUS: OutcomeParams(p0=0.99, t50=240.0, k=0.03),
    Severity.MINOR: OutcomeParams(p0=1.00, t50=1000.0, k=0.01),
    Severity.EXPECTANT: OutcomeParams(p0=0.30, t50=30.0, k=0.05),
}

DEATH_THRESHOLD = 0.05


def survival_probability(
    severity: Severity, minutes: float, deterioration_rate: float = 0.0
) -> float:
    p = OUTCOME_PARAMS[severity]
    z = p.k * (1.0 + deterioration_rate) * (minutes - p.t50)
    z = max(-50.0, min(50.0, z))
    return p.p0 / (1.0 + math.exp(z))


def is_dead(severity: Severity, minutes: float, deterioration_rate: float = 0.0) -> bool:
    return survival_probability(severity, minutes, deterioration_rate) < DEATH_THRESHOLD
