from baselines.nearest import NearestPolicy
from sim.engine import Engine
from sim.entities import PatientStatus
from sim.events import EventType
from sim.generator import generate
from tests.invariants import check_invariants


def test_nearest_surge_run_holds_invariants():
    engine = Engine(generate(7, "surge"), NearestPolicy(), tick_hook=check_invariants)
    engine.run()
    assert engine.tick == engine.end_tick
    assert engine.log.of_type(EventType.COMMITTED)
    assert any(p.status == PatientStatus.IN_TREATMENT for p in engine.patients.values())


def test_nearest_never_uses_mutual_aid_or_loans():
    engine = Engine(generate(7, "surge"), NearestPolicy())
    engine.run()
    kinds = {e.payload["action"]["kind"] for e in engine.log.of_type(EventType.COMMITTED)}
    assert kinds <= {"dispatch", "route"}
