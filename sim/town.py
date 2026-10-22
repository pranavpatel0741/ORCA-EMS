"""Population-based town profile: a fictional square town and its EMS / hospital resources.

Source ratios (U.S., provided by the project owner):
- staffed community-hospital beds: 2.28 per 1,000 residents (AHA via KFF, 2024)
- direct-patient-care physicians: 2.55 per 1,000 (AAMC, 2024)
- practicing nurses: 12.4 per 1,000 (OECD Health at a Glance 2025)

Everything else below is a labeled modeling assumption (see ASSUMPTIONS.md): the steps that
turn town-wide totals into what is on duty in one hospital at one moment.
"""

from __future__ import annotations

import math

from pydantic import BaseModel

# --- source ratios (per resident) ----------------------------------------------------------------
STAFFED_BEDS_PER_CAPITA = 2.28 / 1000
PHYSICIANS_PER_CAPITA = 2.55 / 1000
NURSES_PER_CAPITA = 12.4 / 1000

# --- modeling assumptions ------------------------------------------------------------------------
EMS_CALLS_PER_CAPITA_YEAR = 0.13
DAYTIME_PEAK_FACTOR = 1.4
MINUTES_PER_YEAR = 525_600
ER_SPACES_PER_CAPITA = 0.45 / 1000
HOSPITAL_BASED_SHARE = 0.60  # share of physicians / nurses working in hospitals
SHIFT_FACTOR = 4.2  # staff needed per 24/7 post (168 h / 40 h)
SURGEON_SHARE = 0.06  # share of physicians who can staff a trauma surgical team
BEDS_PER_OR = 25
ER_SPACES_PER_TRAUMA_BAY = 8
RESIDENTS_PER_AMBULANCE = 20_000
STATION_COVERAGE_KM2 = 105  # 10-min drive at 45 km/h, ~5.8 km straight-line radius
ALS_SHARE = 0.4
RESIDENTS_PER_PRIVATE_UNIT = 80_000

# Role shares across hospitals A (trauma L1), B (community), C (trauma L2), D (private).
WARD_SPLIT = {"A": 0.40, "B": 0.25, "C": 0.20, "D": 0.15}
ER_SPLIT = {"A": 0.30, "B": 0.26, "C": 0.26, "D": 0.18}
OR_SPLIT = {"A": 0.40, "C": 0.20, "D": 0.40}
MIN_ER_BEDS = 4

# --- geography -----------------------------------------------------------------------------------
CENTER = (42.35, -71.08)  # fictional town placed at this latitude so km <-> degrees is realistic
KM_PER_DEG_LAT = 111.32


def km_per_deg_lon() -> float:
    return KM_PER_DEG_LAT * math.cos(math.radians(CENTER[0]))


def largest_remainder(total: int, shares: dict[str, float]) -> dict[str, int]:
    """Split an integer total by shares so the parts sum exactly to `total`."""
    raw = {k: total * v / sum(shares.values()) for k, v in shares.items()}
    out = {k: math.floor(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: (out[k] - raw[k], k))[: total - sum(out.values())]:
        out[k] += 1
    return out


class TownProfile(BaseModel):
    population: int = 50_000
    area_km: float = 20.0  # side of the square town

    # --- geography helpers ---------------------------------------------------------------------

    @property
    def origin(self) -> tuple[float, float]:
        """South-west corner (lat, lon)."""
        half = self.area_km / 2
        return (CENTER[0] - half / KM_PER_DEG_LAT, CENTER[1] - half / km_per_deg_lon())

    def to_latlon(self, x_km: float, y_km: float) -> tuple[float, float]:
        lat0, lon0 = self.origin
        return (round(lat0 + y_km / KM_PER_DEG_LAT, 6), round(lon0 + x_km / km_per_deg_lon(), 6))

    def to_km(self, lat: float, lon: float) -> tuple[float, float]:
        lat0, lon0 = self.origin
        return ((lon - lon0) * km_per_deg_lon(), (lat - lat0) * KM_PER_DEG_LAT)

    def scale(self, x_frac: float, y_frac: float) -> tuple[float, float]:
        """Lat/lon of a point given as fractions of the town side (layout is size-independent)."""
        return self.to_latlon(x_frac * self.area_km, y_frac * self.area_km)

    # --- demand --------------------------------------------------------------------------------

    @property
    def calls_per_min(self) -> float:
        return (self.population * EMS_CALLS_PER_CAPITA_YEAR * DAYTIME_PEAK_FACTOR
                / MINUTES_PER_YEAR)

    # --- fleet ---------------------------------------------------------------------------------

    @property
    def city_ambulances(self) -> int:
        by_population = math.ceil(self.population / RESIDENTS_PER_AMBULANCE)
        by_coverage = math.ceil(self.area_km ** 2 / STATION_COVERAGE_KM2)
        return max(by_population, by_coverage)

    @property
    def als_units(self) -> int:
        return max(1, round(self.city_ambulances * ALS_SHARE))

    @property
    def private_units(self) -> int:
        return max(2, round(self.population / RESIDENTS_PER_PRIVATE_UNIT))

    @property
    def police_units(self) -> int:
        return max(2, round(self.population / 100_000))

    @property
    def fire_units(self) -> int:
        return max(1, round(self.population / 150_000))

    # --- hospitals -----------------------------------------------------------------------------

    @property
    def staffed_beds(self) -> int:
        return round(self.population * STAFFED_BEDS_PER_CAPITA)

    @property
    def ward_beds(self) -> dict[str, int]:
        return largest_remainder(self.staffed_beds, WARD_SPLIT)

    @property
    def er_spaces(self) -> int:
        return round(self.population * ER_SPACES_PER_CAPITA)

    @property
    def er_beds(self) -> dict[str, int]:
        split = largest_remainder(self.er_spaces, ER_SPLIT)
        return {k: max(MIN_ER_BEDS, v) for k, v in split.items()}

    @property
    def physicians_on_duty(self) -> float:
        return self.population * PHYSICIANS_PER_CAPITA * HOSPITAL_BASED_SHARE / SHIFT_FACTOR

    @property
    def surgical_teams(self) -> dict[str, int]:
        total = self.population * PHYSICIANS_PER_CAPITA * SURGEON_SHARE / SHIFT_FACTOR
        return {"A": max(1, round(total * 0.6)), "C": max(1, round(total * 0.4))}

    @property
    def hospital_nurses_on_duty(self) -> float:
        return self.population * NURSES_PER_CAPITA * HOSPITAL_BASED_SHARE / SHIFT_FACTOR

    @property
    def ed_nurses(self) -> dict[str, int]:
        beds = self.er_beds
        ed_share = sum(beds.values()) / (sum(beds.values()) + self.staffed_beds)
        total = max(len(beds), round(self.hospital_nurses_on_duty * ed_share))
        return {k: max(1, v) for k, v in largest_remainder(total, beds).items()}

    @property
    def operating_rooms(self) -> dict[str, int]:
        total = max(3, round(self.staffed_beds / BEDS_PER_OR))
        return largest_remainder(total, OR_SPLIT)

    @property
    def trauma_bays(self) -> dict[str, int]:
        total = max(2, round(self.er_spaces / ER_SPACES_PER_TRAUMA_BAY))
        return largest_remainder(total, {"A": 2, "C": 1})

    def summary(self) -> dict:
        """Derived numbers, stored in the scenario for the dashboard header and the report."""
        return {
            "population": self.population,
            "area_km": self.area_km,
            "calls_per_hour": round(self.calls_per_min * 60, 3),
            "city_ambulances": self.city_ambulances,
            "private_units": self.private_units,
            "police_units": self.police_units,
            "fire_units": self.fire_units,
            "staffed_beds": self.staffed_beds,
            "ward_beds": self.ward_beds,
            "er_beds": self.er_beds,
            "physicians_on_duty": round(self.physicians_on_duty, 1),
            "surgical_teams": self.surgical_teams,
            "hospital_nurses_on_duty": round(self.hospital_nurses_on_duty, 1),
            "ed_nurses": self.ed_nurses,
            "operating_rooms": self.operating_rooms,
            "trauma_bays": self.trauma_bays,
        }
