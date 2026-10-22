import math

import pytest

from sim.town import STATION_COVERAGE_KM2, TownProfile, largest_remainder


def test_default_town_matches_derivation():
    t = TownProfile()
    assert t.population == 50_000 and t.area_km == 20
    assert 1 / t.calls_per_min == pytest.approx(57.8, abs=0.5)  # ~1 call per 58 min
    assert t.city_ambulances == 4  # coverage-based beats population-based (3)
    assert t.staffed_beds == 114
    assert t.ward_beds == {"A": 46, "B": 28, "C": 23, "D": 17}
    assert sum(t.er_beds.values()) == 22
    assert t.surgical_teams == {"A": 1, "C": 1}
    assert t.physicians_on_duty == pytest.approx(18.2, abs=0.1)
    assert t.hospital_nurses_on_duty == pytest.approx(88.6, abs=0.1)


@pytest.mark.parametrize("field", ["calls_per_min", "staffed_beds", "er_spaces",
                                   "city_ambulances", "hospital_nurses_on_duty"])
def test_resources_grow_with_population(field):
    values = [getattr(TownProfile(population=p), field) for p in (50_000, 150_000, 400_000)]
    assert values == sorted(values) and values[0] < values[-1]


def test_largest_remainder_sums_exactly():
    for total in (0, 1, 7, 22, 114):
        assert sum(largest_remainder(total, {"A": 0.4, "B": 0.25, "C": 0.2, "D": 0.15}).values()) \
            == total


def test_station_coverage_radius():
    radius_km = math.sqrt(STATION_COVERAGE_KM2 / math.pi)
    minutes = radius_km * 1.3 / 45 * 60
    assert 9 <= minutes <= 11  # one station covers about a 10-minute drive


def test_km_latlon_roundtrip():
    t = TownProfile()
    x, y = t.to_km(*t.to_latlon(13.0, 7.5))
    assert x == pytest.approx(13.0, abs=1e-3) and y == pytest.approx(7.5, abs=1e-3)
    from sim.travel import haversine_km
    assert haversine_km(t.to_latlon(0, 0), t.to_latlon(20, 0)) == pytest.approx(20, rel=0.01)
