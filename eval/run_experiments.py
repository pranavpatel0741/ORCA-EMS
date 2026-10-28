"""Experiment grid (PLAN §17).

    python eval/run_experiments.py --seeds 5
    python eval/run_experiments.py --seeds 5 --policies nearest rule_based   # baselines only
    python eval/run_experiments.py --seeds 5 --backend scripted               # offline dry run

Paired design: every policy runs on the same scenario files (same seed -> same calls, patients,
hospital load). Results go to results/runs/<run>.json (one file per run, so the grid is
resumable) and then results/summary.csv, results/summary.md via eval/report_tables.py.

LLM policies (agents, agents_no_negotiation) use the OpenAI backend when OPENAI_API_KEY and
OPENAI_MODEL are set (LLM_MODE=record or live), or replay data/llm_cache in cache_only mode.
`--backend scripted` uses the deterministic stand-in; those runs are labeled "scripted" and are
never reported as LLM results.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import LOG_DIR, RESULTS_DIR  # noqa: E402
from eval.metrics import compute_metrics  # noqa: E402

POLICIES = ["nearest", "rule_based", "agents_no_negotiation", "agents"]
LLM_POLICIES = {"agents", "agents_no_negotiation"}
INFOS = ["complete", "partial"]
DEMANDS = ["normal", "surge"]
RUNS_DIR = RESULTS_DIR / "runs"


def out_dir(backend: str) -> Path:
    """Scripted dry runs live apart from real results so they can never be mixed in."""
    return RESULTS_DIR / "scripted" if backend == "scripted" else RESULTS_DIR


def run_key(policy: str, info: str, demand: str, seed: int, backend: str) -> str:
    tag = f"_{backend}" if policy in LLM_POLICIES and backend != "openai" else ""
    return f"{policy}{tag}__{demand}__{info}__s{seed:02d}"


def make_policy(policy: str, backend: str):
    if policy in LLM_POLICIES:
        from orca_agents.llm_cache import LLMClient
        from orca_agents.orchestrator import AgentPolicy, default_client
        if backend == "scripted":
            from orca_agents.scripted import ScriptedBackend
            client = LLMClient(ScriptedBackend(), mode="live",
                               cache_dir=RESULTS_DIR / "scripted" / "cache")
        else:
            client = default_client()
        return AgentPolicy(negotiate=policy == "agents", client=client)
    from run import make_policy as baseline
    return baseline(policy)


def run_cell(args: tuple[str, str, str, int, str]) -> dict:
    policy, info, demand, seed, backend = args
    from sim.engine import Engine
    from sim.generator import generate
    from sim.travel import load_timing

    key = run_key(policy, info, demand, seed, backend)
    out = out_dir(backend) / "runs" / f"{key}.json"
    if out.exists():
        return json.loads(out.read_text())
    started = time.perf_counter()
    engine = Engine(generate(seed, demand), make_policy(policy, backend), timing=load_timing(),
                    info=info, run_id=key)
    engine.run()
    engine.log.write_jsonl(LOG_DIR / "experiments" / f"{key}.jsonl")
    record = {"key": key, "policy": policy, "backend": backend if policy in LLM_POLICIES
              else "none", "info": info, "demand": demand, "seed": seed,
              "wall_seconds": round(time.perf_counter() - started, 2),
              "metrics": compute_metrics(engine.log.events)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, sort_keys=True))
    return record


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Run the ORCA-EMS experiment grid.")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--policies", nargs="+", choices=POLICIES, default=POLICIES)
    ap.add_argument("--backend", choices=["openai", "scripted"], default="openai")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)

    cells = [(p, i, d, s, args.backend) for p in args.policies for d in DEMANDS for i in INFOS
             for s in range(1, args.seeds + 1)]
    baseline_cells = [c for c in cells if c[0] not in LLM_POLICIES]
    llm_cells = [c for c in cells if c[0] in LLM_POLICIES]
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results += list(pool.map(run_cell, baseline_cells))
    for c in llm_cells:  # sequential: API rate limits and a shared response cache
        try:
            results.append(run_cell(c))
        except Exception as exc:  # noqa: BLE001 - report and keep the grid resumable
            print(f"skipped {run_key(*c)}: {exc}")
    print(f"{len(results)} runs in results/runs/")

    from eval.report_tables import write_reports
    paths = write_reports(out_dir(args.backend) / "runs", out_dir(args.backend))
    for p in paths:
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
