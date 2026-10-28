import os
import subprocess
import sys
from pathlib import Path

from eval.metrics import compute_metrics, headline
from run import run_once
from sim.events import EventType

ROOT = Path(__file__).resolve().parent.parent


def _run_in_process(tmp: Path, hash_seed: str) -> bytes:
    code = ("from pathlib import Path; from run import run_once; "
            f"run_once('rule_based', 'surge', 'partial', 7, log_dir=Path(r'{tmp}'))")
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True,
                   env={**os.environ, "PYTHONHASHSEED": hash_seed})
    return (tmp / "run_s07_surge_partial_rule_based.jsonl").read_bytes()


def test_same_seed_and_policy_give_identical_logs_across_processes(tmp_path):
    a = _run_in_process(tmp_path / "a", "1")
    b = _run_in_process(tmp_path / "b", "2")
    assert a == b


def test_run_once_writes_log_and_metrics(tmp_path):
    engine, path, metrics = run_once("nearest", "normal", "complete", 3, log_dir=tmp_path)
    assert path.exists() and metrics["calls"] == len(engine.log.of_type(EventType.CALL_RECEIVED))
    h = headline(metrics)
    assert h["llm_calls"] == 0 and h["deaths"] >= 0


def test_metrics_on_lifecycle_log():
    from tests.test_engine import run_lifecycle
    m = compute_metrics(run_lifecycle().log.events)
    assert m["response_time"]["mean"] == 19  # call 2, on scene 21
    assert m["time_to_care_by_severity"]["SERIOUS"]["mean"] == 37
    assert m["ambulance_minutes_at_er_over_base"] == 0  # 5 min offload < 10 base
    assert m["deaths"] == 0 and m["unserved_calls_30min"] == 0


def test_cli_prints_headline():
    out = subprocess.run([sys.executable, "run.py", "--policy", "nearest", "--demand",
                          "normal", "--seed", "3"], cwd=ROOT, capture_output=True, text=True,
                         check=True)
    assert "deaths" in out.stdout and "log:" in out.stdout
