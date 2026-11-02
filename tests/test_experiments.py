import json

from eval.metrics import compute_metrics
from eval.report_tables import load_runs, paired, verdict, write_reports
from run import run_once


def test_write_reports_from_runs(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    for policy in ("nearest", "rule_based"):
        for seed in (1, 2):
            engine, _, metrics = run_once(policy, "surge", "partial", seed, log_dir=tmp_path)
            (runs / f"{policy}_{seed}.json").write_text(
                json.dumps(
                    {
                        "policy": policy,
                        "backend": "none",
                        "info": "partial",
                        "demand": "surge",
                        "seed": seed,
                        "wall_seconds": 0.1,
                        "metrics": metrics,
                    }
                )
            )
    csv, md = write_reports(runs, tmp_path)
    text = md.read_text()
    assert "### Surge demand · partial information" in text and "| rule_based |" in text
    assert "LLM agent runs are pending" in text
    df = load_runs(runs)
    r = paired(df, "rule_based", "nearest", "capacity_failures", demand="surge")
    assert r["n"] == 2 and verdict(r) in ("supported", "mixed", "not supported")
    assert csv.read_text().startswith("policy,demand,info")


def test_verdict_rules():
    assert verdict({"n": 5, "mean": 1.0, "wins": 4, "losses": 1}) == "supported"
    assert verdict({"n": 5, "mean": -1.0, "wins": 1, "losses": 4}) == "not supported"
    assert verdict({"n": 5, "mean": 0.5, "wins": 3, "losses": 2}) == "mixed"
    assert verdict(None).startswith("not tested")


def test_metrics_are_json_serializable():
    engine, _, metrics = run_once("rule_based", "normal", "complete", 2)
    json.dumps(metrics)
    assert compute_metrics(engine.log.events) == metrics


def test_reports_reject_mixed_backends_and_duplicate_cells():
    import pandas as pd
    import pytest

    from eval.report_tables import validate_runs

    row = {"policy": "agents", "backend": "openai", "demand": "surge", "info": "partial", "seed": 1}
    with pytest.raises(ValueError, match="Mixed agent backends"):
        validate_runs(
            pd.DataFrame([row, {**row, "policy": "agents_no_negotiation", "backend": "scripted"}])
        )
    with pytest.raises(ValueError, match="Duplicate experiment cells"):
        validate_runs(pd.DataFrame([row, row]))


def test_resume_rejects_historical_results(tmp_path, monkeypatch):
    import pytest

    import eval.run_experiments as experiments

    monkeypatch.setattr(experiments, "out_dir", lambda backend: tmp_path)
    runs = tmp_path / "runs"
    runs.mkdir()
    key = experiments.run_key("nearest", "partial", "normal", 1, "openai")
    (runs / f"{key}.json").write_text(json.dumps({"policy": "nearest"}))
    with pytest.raises(ValueError, match="historical or stale"):
        experiments.run_cell(("nearest", "partial", "normal", 1, "openai"))
    monkeypatch.setattr(experiments, "LOG_DIR", tmp_path / "logs")
    refreshed = experiments.run_cell(("nearest", "partial", "normal", 1, "openai", True))
    assert refreshed["fingerprint"]
    assert experiments.run_cell(("nearest", "partial", "normal", 1, "openai")) == refreshed


def test_resume_fingerprint_tracks_model(monkeypatch):
    import eval.run_experiments as experiments

    monkeypatch.setattr(experiments.settings, "OPENAI_MODEL", "model-a")
    first = experiments.evaluation_fingerprint("agents", "openai")
    monkeypatch.setattr(experiments.settings, "OPENAI_MODEL", "model-b")
    assert experiments.evaluation_fingerprint("agents", "openai") != first
