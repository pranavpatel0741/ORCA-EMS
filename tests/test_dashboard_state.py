from app.state import CALL, build_state
from baselines.nearest import NearestPolicy
from sim.engine import Engine
from sim.events import EventType
from sim.generator import generate
from tests.test_engine import run_lifecycle


def surge_engine(until=None):
    engine = Engine(generate(7, "surge"), NearestPolicy())
    engine.run(until=until)
    return engine


def test_hospital_capacity_matches_engine_snapshot():
    engine = surge_engine(until=90)
    state = build_state(engine.log.events, upto=engine.tick)
    assert state.tick == engine.tick
    for hid, hs in engine.hospitals.items():
        snap = hs.snapshot()
        assert state.hospitals[hid]["occupied"] == snap["occupied"]
        assert state.hospitals[hid]["totals"] == snap["totals"]


def test_admission_lowers_free_er_beds_and_is_explained():
    state_before = build_state(run_lifecycle().log.events, upto=38)
    state_after = build_state(run_lifecycle().log.events, upto=39)
    h0, h1 = state_before.hospitals["H"], state_after.hospitals["H"]
    free = lambda h: h["totals"]["er_bed"] - h["occupied"]["er_bed"]  # noqa: E731
    assert free(h1) == free(h0) - 1
    assert state_after.hospital_changes["H"][-1] == "t=39: admitted P-1 via AMB-1"


def test_call_thread_contains_call_and_patient_events():
    engine = surge_engine()
    state = build_state(engine.log.events)
    for inc_id in state.incidents:
        thread = state.threads[inc_id]
        assert thread[0].category == CALL and thread[0].kind == "911 CALL"
    bus = state.threads["MCI-2"]
    assert any(r.kind == "SCENE REPORT" for r in bus)
    assert any("in definitive care" in r.text for r in bus)


def test_replay_matches_live(tmp_path):
    engine = surge_engine(until=120)
    path = engine.log.write_jsonl(tmp_path / "run.jsonl")
    from sim.events import read_jsonl
    live, replay = build_state(engine.log.events), build_state(read_jsonl(path))
    assert live.kpis == replay.kpis and live.hospitals == replay.hospitals
    assert [r.text for r in live.feed] == [r.text for r in replay.feed]


def test_kpis_and_units_are_consistent():
    engine = surge_engine(until=60)
    state = build_state(engine.log.events)
    called = sum(1 for p in engine.patients.values()
                 if p.incident_id in engine.active_or_closed())
    k = state.kpis
    assert k["waiting_on_scene"] + k["in_transport"] + k["waiting_at_er"] + k["in_care"] + \
        k["deceased"] == called
    assert k["units"] == len(engine.activated_units)
    for uid, amb in engine.ambulances.items():
        assert state.units[uid]["state"] == amb.state
    assert len(engine.log.of_type(EventType.CALL_RECEIVED)) == k["calls"]
