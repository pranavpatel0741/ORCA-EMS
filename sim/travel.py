"""Travel times, ETA estimates, and duration sampling (PLAN §9).

`TimingConfig` holds every sampled duration as an inclusive (lo, hi) minute range. Setting
lo == hi and `noise_sigma = 0` gives a fully deterministic configuration for hand-checked tests.
"""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel

from sim.entities import Location

MinuteRange = tuple[int, int]
Z90 = 1.2816  # standard-normal 90th percentile


class TimingConfig(BaseModel):
    road_factor: float = 1.3
    emergency_kmh: float = 45.0
    return_kmh: float = 35.0
    noise_sigma: float = 0.15

    scene_time_critical: MinuteRange = (8, 15)
    scene_time_other: MinuteRange = (5, 10)
    loading: MinuteRange = (3, 6)
    handover: MinuteRange = (5, 10)

    # Offload wait bands by ER occupancy at arrival: (upper bound exclusive, range).
    offload_bands: list[tuple[float, MinuteRange]] = [
        (0.80, (5, 12)),
        (0.95, (15, 35)),
        (math.inf, (35, 60)),
    ]
    offload_per_queued_patient: int = 5  # added per queued patient in the top band
    base_handover_min: int = 10  # PLAN §16: ER minutes beyond this count as offload delay

    # Treatment durations
    trauma_bay: MinuteRange = (30, 60)
    operating_room: MinuteRange = (60, 180)
    er_serious: MinuteRange = (60, 180)
    er_minor: MinuteRange = (30, 90)
    er_background: MinuteRange = (60, 240)

    # Scene operations
    staging_offset_km: float = 0.5

    # Staff loans
    staff_transfer: MinuteRange = (20, 30)
    staff_loan_duration: int = 120

    @classmethod
    def deterministic(cls, **overrides: object) -> TimingConfig:
        """Zero noise; each range collapsed to its lower bound unless overridden."""
        base = cls()
        fields: dict[str, object] = {"noise_sigma": 0.0}
        for name in cls.model_fields:
            value = getattr(base, name)
            if isinstance(value, tuple) and len(value) == 2:
                fields[name] = (value[0], value[0])
        fields["offload_bands"] = [(ub, (r[0], r[0])) for ub, r in base.offload_bands]
        fields.update(overrides)
        return cls(**fields)


def haversine_km(a: Location, b: Location) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(
        (lon2 - lon1) / 2
    ) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def base_minutes(a: Location, b: Location, cfg: TimingConfig, *, emergency: bool = True) -> float:
    speed = cfg.emergency_kmh if emergency else cfg.return_kmh
    return haversine_km(a, b) * cfg.road_factor / speed * 60.0


class Sampler:
    """All stochastic durations, drawn from the run's seeded generator."""

    def __init__(self, rng: np.random.Generator, cfg: TimingConfig) -> None:
        self.rng = rng
        self.cfg = cfg

    def minutes(self, r: MinuteRange) -> int:
        lo, hi = r
        if lo == hi:
            return lo
        return int(self.rng.integers(lo, hi + 1))

    def travel(self, a: Location, b: Location, *, emergency: bool = True) -> int:
        noise = 1.0 if self.cfg.noise_sigma == 0 else float(
            self.rng.lognormal(0.0, self.cfg.noise_sigma)
        )
        return max(1, round(base_minutes(a, b, self.cfg, emergency=emergency) * noise))

    def offload(self, occupancy: float, queue_len: int) -> int:
        for upper, r in self.cfg.offload_bands:
            if occupancy < upper:
                extra = queue_len * self.cfg.offload_per_queued_patient if math.isinf(upper) else 0
                return self.minutes(r) + extra
        raise AssertionError("offload bands must end with +inf")


def estimate_eta(a: Location, b: Location, cfg: TimingConfig) -> dict[str, float]:
    """ETA summary from the same model the engine samples from. Exposed to agents and baselines."""
    median = max(1.0, base_minutes(a, b, cfg))
    p90 = median * math.exp(Z90 * cfg.noise_sigma)
    return {"median_min": round(median, 1), "p90_min": round(p90, 1)}


def offset_point(origin: Location, toward: Location, km: float) -> Location:
    """A point `km` from `origin` along the line toward `toward` (used for staging)."""
    d = haversine_km(origin, toward)
    if d == 0:
        return (origin[0] + km / 111.0, origin[1])
    f = km / d
    return (origin[0] + (toward[0] - origin[0]) * f, origin[1] + (toward[1] - origin[1]) * f)


def interpolate(a: Location, b: Location, frac: float) -> Location:
    frac = min(1.0, max(0.0, frac))
    return (a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac)
