from baselines.rule_based import RuleBasedPolicy
from eval.run_report import load_index, save_run
from sim.engine import Engine
from sim.events import read_jsonl
from sim.presets import build_preset


def test_save_run_writes_log_transcript_scorecard_and_index(tmp_path):
    engine = Engine(build_preset("Shooting"), RuleBasedPolicy())
    engine.run()
    folder = save_run(engine.log.events, "Shooting", out_dir=tmp_path)
    assert len(read_jsonl(folder / "events.jsonl")) == len(engine.log.events)
    text = (folder / "transcript.md").read_text()
    assert "## How well it went" in text and "Deaths" in text and "911 CALL" in text
    assert (folder / "scorecard.json").exists()
    save_run(engine.log.events, "Shooting", out_dir=tmp_path)
    rows = load_index(tmp_path)
    assert len(rows) == 2 and rows[0]["incident"] == "Shooting"
    assert rows[0]["policy"] == "rule_based"
