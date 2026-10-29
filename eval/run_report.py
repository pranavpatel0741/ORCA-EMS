"""Save one run as a folder a person can read: event log, transcript, and scorecard.

    results/runs_saved/<stamp>_<incident>_<policy>/
        events.jsonl    full event log (replays exactly on the dashboard)
        transcript.md   the conversation, each line labeled with who produced it, plus the
                        negotiation threads
        scorecard.json  every metric (eval/metrics.py) plus AI vs rule-backup decision counts
    results/runs_saved/index.csv   one row per saved run, to compare runs side by side
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from app.state import build_state, negotiation_threads
from config.settings import RESULTS_DIR
from eval.metrics import compute_metrics, headline
from sim.events import Event, EventType

SAVE_DIR = RESULTS_DIR / "runs_saved"
SOURCE_LABEL = {"ai": "AI", "standin": "stand-in (not AI)", "backup": "rule backup",
                "rules": "rules", "sim": "sim"}

# Plain-language scorecard lines: (label, headline key, unit or formatter)
SCORECARD = [
    ("Deaths", "deaths", ""),
    ("Critical patients in care within 60 min", "critical_on_time", "pct"),
    ("Critical patients: call to definitive care (mean)", "critical_care_mean", "min"),
    ("Call to first ambulance on scene (mean)", "response_mean", "min"),
    ("Ambulance minutes waiting at ER doors (beyond 10 min)", "er_wait_over_base", "min"),
    ("Hospital minutes over capacity", "overload_min", "min"),
    ("Calls with no ambulance after 30 min", "unserved_calls", ""),
    ("Patients still not in care at the end", "not_in_care_end", ""),
    ("Proposals blocked by safety rules", "rejections", ""),
    ("Decisions sent for human review", "escalations", ""),
    ("Synthetic outcome score (higher is better)", "outcome_score", ""),
    ("AI calls", "llm_calls", ""),
    ("AI tokens", "llm_tokens", ""),
]


def _fmt(value: Any, unit: str) -> str:
    if value is None:
        return "n/a"
    if unit == "pct":
        return f"{value:.0%}"
    if isinstance(value, float):
        value = round(value, 1)
    return f"{value} {unit}".strip()


def decision_sources(events: list[Event]) -> dict[str, int]:
    """Committed decisions by who made them: AI agents, the rule backup, or a baseline."""
    out: Counter = Counter()
    for e in events:
        if e.type == EventType.COMMITTED:
            by = e.payload["action"].get("decided_by", "")
            out[{"ai": "ai", "rules": "rule_backup"}.get(by, "baseline_rules")] += 1
    return {k: out.get(k, 0) for k in ("ai", "rule_backup", "baseline_rules")}


def scorecard(events: list[Event]) -> dict[str, Any]:
    m = compute_metrics(events)
    started = next(e.payload for e in events if e.type == EventType.RUN_STARTED)
    calls = [e.payload for e in events if e.type == EventType.LLM_CALL]
    return {"run_id": events[0].run_id, "policy": started.get("policy"),
            "info": started.get("info"), "seed": started.get("seed"),
            "model": calls[0]["model"] if calls else None,
            "minutes": events[-1].tick, "headline": headline(m),
            "decisions": decision_sources(events), "metrics": m}


def transcript(events: list[Event], title: str, card: dict[str, Any]) -> str:
    state = build_state(events)
    h, d = card["headline"], card["decisions"]
    lines = [f"# {title}", "",
             f"Policy: {card['policy']} · model: {card['model'] or 'none'} · "
             f"information: {card['info']} · seed {card['seed']} · "
             f"{card['minutes']} simulated minutes", "", "## How well it went", "",
             "| Measure | Value |", "|---|---|"]
    lines += [f"| {label} | {_fmt(h.get(key), unit)} |" for label, key, unit in SCORECARD]
    lines += [f"| Decisions by AI agents | {d['ai']} |",
              f"| Decisions by the rule backup | {d['rule_backup']} |", "",
              "## Negotiations", ""]
    threads = negotiation_threads(events)
    if not threads:
        lines.append("No negotiations (baselines do not negotiate).")
    for t in threads:
        out = t["outcome"]
        end = f"→ Hospital {out['hospital']} (decided by {out['by']})" if out else "→ open"
        lines += ["", f"**{t['unit']}** · {t['patients']} patient(s) · {t['incident']} {end}"]
        lines += [f"- {x['tick']:>3} min · {x['sender']} → {x['recipient']} · {x['type']} "
                  f"[{SOURCE_LABEL[x['source']]}]: {x['text']}" for x in t["turns"]]
    lines += ["", "## Full conversation", ""]
    lines += [f"- {r.tick:>3} min · {r.sender} → {r.recipient} · {r.kind} "
              f"[{SOURCE_LABEL.get(r.source, r.source)}]: {r.text}" for r in state.feed]
    return "\n".join(lines) + "\n"


def save_run(events: list[Event], incident: str, out_dir: Path = SAVE_DIR) -> Path:
    """Write the run folder and append a row to the index. Returns the folder."""
    card = scorecard(events)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", f"{incident}_{card['policy']}".lower()).strip("-")
    folder = out_dir / f"{stamp}_{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "events.jsonl").open("w") as f:
        for e in events:
            f.write(json.dumps(e.model_dump(mode="json"), sort_keys=True) + "\n")
    (folder / "scorecard.json").write_text(json.dumps(card, indent=1, default=str))
    (folder / "transcript.md").write_text(
        transcript(events, f"{incident} · {card['policy']}", card))
    row = {"saved": stamp, "incident": incident, "policy": card["policy"],
           "model": card["model"] or "", "info": card["info"], "seed": card["seed"],
           "minutes": card["minutes"], **card["headline"],
           "ai_decisions": card["decisions"]["ai"],
           "rule_backup_decisions": card["decisions"]["rule_backup"], "folder": folder.name}
    index = out_dir / "index.csv"
    new = not index.exists()
    with index.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    return folder


def load_index(out_dir: Path = SAVE_DIR) -> list[dict[str, str]]:
    index = out_dir / "index.csv"
    if not index.exists():
        return []
    with index.open() as f:
        return list(csv.DictReader(f))
