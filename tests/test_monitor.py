from baselines.nearest import NearestPolicy
from sim.engine import Engine
from sim.events import EventType
from sim.generator import generate


def alerts(engine):
    return [e.payload for e in engine.log.of_type(EventType.MONITOR_ALERT)]


def test_surge_raises_expected_alerts_and_clears_them():
    engine = Engine(generate(7, "surge"), NearestPolicy())
    engine.run()
    raised = {(a["alert"], a["key"]) for a in alerts(engine) if a["phase"] == "RAISED"}
    kinds = {k for k, _ in raised}
    assert {"SURGE", "HOSPITAL_FULL", "NO_FREE_UNITS"} <= kinds
    # Every alert raise/clear alternates per key: never raised twice in a row.
    last: dict = {}
    for a in alerts(engine):
        key = (a["alert"], a["key"])
        assert last.get(key) != a["phase"]
        last[key] = a["phase"]


def test_normal_day_has_no_surge_alert_at_start():
    engine = Engine(generate(7, "normal"), NearestPolicy())
    engine.run(until=5)
    assert not any(a["alert"] == "SURGE" for a in alerts(engine))
