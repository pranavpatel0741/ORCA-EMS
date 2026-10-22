from baselines.nearest import NearestPolicy
from eval.handling import by_severity, call_handling, decision_time, patient_handling
from sim.engine import Engine
from sim.generator import generate
from tests.test_engine import run_lifecycle


def test_lifecycle_handling_times_match_hand_checked_timestamps():
    """Call at 2; dispatch at 2; on scene 21; at hospital 39; definitive care 39."""
    rows = call_handling(run_lifecycle().log.events)
    assert len(rows) == 1
    r = rows[0]
    assert (r["decision_min"], r["scene_min"], r["hospital_min"]) == (0, 19, 37)
    assert (r["care_mean_min"], r["care_max_min"], r["in_care"]) == (37, 37, 1)
    assert r["rejections"] == 0 and r["deceased"] == 0 and r["messages"] == 1  # PRE_ALERT


def test_patient_and_severity_tables():
    engine = Engine(generate(7, "surge"), NearestPolicy())
    engine.run()
    patients = patient_handling(engine.log.events)
    assert len(patients) == len(engine.patients)
    sev = {r["severity"]: r for r in by_severity(patients)}
    assert sev["CRITICAL"]["patients"] == sum(
        1 for p in engine.patients.values() if p.true_severity == "CRITICAL")
    calls = call_handling(engine.log.events)
    assert {r["incident_id"] for r in calls} == set(engine.incidents)


def test_decision_time_summary():
    engine = Engine(generate(7, "normal"), NearestPolicy())
    engine.run()
    d = decision_time(engine.decision_timings, engine.log.events)
    assert d["decisions"] >= 1 and d["total_ms"] > 0 and d["llm_calls"] == 0
