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


def test_saved_scripted_run_does_not_claim_ai_decisions(tmp_path):
    import json

    from orca_agents.llm_cache import LLMClient
    from orca_agents.orchestrator import AgentPolicy
    from orca_agents.scripted import ScriptedBackend

    engine = Engine(
        build_preset("Cardiac arrest"),
        AgentPolicy(client=LLMClient(ScriptedBackend(), mode="live", cache_dir=tmp_path / "cache")),
    )
    engine.run()
    folder = save_run(engine.log.events, "Scripted", out_dir=tmp_path / "saved")
    card = json.loads((folder / "scorecard.json").read_text())
    assert card["decisions"]["ai"] == 0
    assert card["decisions"]["scripted_agents"] > 0
    assert "stand-ins (not AI)" in (folder / "transcript.md").read_text()
