"""Run one scenario with one policy and print its metrics.

    python run.py --policy rule_based --demand surge --info partial --seed 7
    python run.py --policy agents --preset "School bus crash"

Writes logs/run_<id>.jsonl. LLM policies need OPENAI_API_KEY / OPENAI_MODEL in .env unless
LLM_MODE=cache_only and the responses are already cached in data/llm_cache/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from config.settings import LOG_DIR
from eval.metrics import compute_metrics, headline
from sim.engine import Engine
from sim.generator import DEFAULT_POPULATION, generate
from sim.presets import PRESETS, build_preset
from sim.travel import load_timing

POLICY_NAMES = ["nearest", "rule_based", "agents_no_negotiation", "agents"]


def make_policy(name: str):
    if name == "nearest":
        from baselines.nearest import NearestPolicy
        return NearestPolicy()
    if name == "rule_based":
        from baselines.rule_based import RuleBasedPolicy
        return RuleBasedPolicy()
    if name in ("agents", "agents_no_negotiation"):
        from orca_agents.orchestrator import AgentPolicy
        return AgentPolicy(negotiate=name == "agents")
    raise ValueError(f"unknown policy {name}")


def run_once(policy: str, demand: str = "surge", info: str = "partial", seed: int = 7,
             population: int = DEFAULT_POPULATION, preset: str | None = None,
             log_dir: Path = LOG_DIR) -> tuple[Engine, Path, dict]:
    scenario = build_preset(preset, seed, population) if preset else \
        generate(seed, demand, population)
    engine = Engine(scenario, make_policy(policy), timing=load_timing(), info=info)
    engine.run()
    path = engine.log.write_jsonl(log_dir / f"run_{engine.run_id}.jsonl")
    return engine, path, compute_metrics(engine.log.events)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Run one ORCA-EMS scenario.")
    ap.add_argument("--policy", choices=POLICY_NAMES, default="rule_based")
    ap.add_argument("--demand", choices=["normal", "surge"], default="surge")
    ap.add_argument("--preset", choices=list(PRESETS), default=None)
    ap.add_argument("--info", choices=["complete", "partial"], default="partial")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--population", type=int, default=DEFAULT_POPULATION)
    ap.add_argument("--json", action="store_true", help="print all metrics as JSON")
    ap.add_argument("--save", action="store_true",
                    help="also save transcript + scorecard to results/runs_saved/")
    args = ap.parse_args(argv)
    engine, path, metrics = run_once(args.policy, args.demand, args.info, args.seed,
                                     args.population, args.preset)
    print(f"log: {path}")
    if args.save:
        from eval.run_report import save_run
        print(f"saved: {save_run(engine.log.events, args.preset or args.demand)}")
    if args.json:
        print(json.dumps(metrics, indent=2))
        return
    for k, v in headline(metrics).items():
        print(f"  {k:<20} {v}")


if __name__ == "__main__":
    main()
