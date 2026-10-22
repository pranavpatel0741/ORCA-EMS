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
    ward_stay: MinuteRange = (2880, 10080)  # inpatient stay, 2-7 days

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


# Fixed stream ids. Each purpose draws from its own generator so that a policy's decisions do
# not shift unrelated randomness (paired experiment design, PLAN §17).
STREAMS = {"travel": 1, "background": 2, "staff": 3, "misc": 4}
PATIENT_STREAM = 200
PATIENT_DRAWS = ("scene", "loading", "offload", "handover", "bay", "or", "er")


def from_uniform(r: MinuteRange, u: float) -> int:
    """Map u in [0, 1) onto the inclusive integer range r."""
    lo, hi = r
    if lo == hi:
        return lo
    return min(hi, lo + int(u * (hi - lo + 1)))


class Sampler:
    """Stochastic durations from named, seeded streams.

    - `travel`: travel-time noise (necessarily depends on which trips a policy makes)
    - `background`: background hospital arrivals and their stays (policy-independent)
    - `staff`: staff-loan transfer delays
    - per-patient common random numbers: scene, loading, offload, handover, and treatment
      draws are fixed per patient, so two policies that treat the same patient give the same
      durations for the same circumstances.
    """

    def __init__(self, seed: int, cfg: TimingConfig) -> None:
        self.seed = seed
        self.cfg = cfg
        self.streams = {name: np.random.default_rng([seed, sid]) for name, sid in STREAMS.items()}

    def stream(self, name: str) -> np.random.Generator:
        return self.streams[name]

    def patient_uniforms(self, index: int) -> dict[str, float]:
        rng = np.random.default_rng([self.seed, PATIENT_STREAM, index])
        return dict(zip(PATIENT_DRAWS, rng.random(len(PATIENT_DRAWS)).tolist(), strict=True))

    def minutes(self, r: MinuteRange, u: float | None = None, stream: str = "misc") -> int:
        if r[0] == r[1]:
            return r[0]
        if u is None:
            u = float(self.streams[stream].random())
        return from_uniform(r, u)

    def travel(self, a: Location, b: Location, *, emergency: bool = True) -> int:
        noise = 1.0 if self.cfg.noise_sigma == 0 else float(
            self.streams["travel"].lognormal(0.0, self.cfg.noise_sigma)
        )
        return max(1, round(base_minutes(a, b, self.cfg, emergency=emergency) * noise))

    def offload_band(self, occupancy: float, queue_len: int, u: float | None = None) -> int:
        """Crowding-driven minimum offload time (PLAN §9)."""
        for upper, r in self.cfg.offload_bands:
            if occupancy < upper:
                extra = queue_len * self.cfg.offload_per_queued_patient if math.isinf(upper) else 0
                return self.minutes(r, u) + extra
        raise AssertionError("offload bands must end with +inf")


def midpoint(r: MinuteRange) -> float:
    return (r[0] + r[1]) / 2


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
