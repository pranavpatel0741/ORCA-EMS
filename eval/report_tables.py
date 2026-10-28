"""Results tables (PLAN §17): summary.csv and summary.md from results/runs/*.json.

Every cell (policy x demand x information) reports mean and standard deviation over seeds.
Hypotheses are checked with paired per-seed comparisons on the same scenarios. With few seeds
these are descriptive, not statistical proof; summary.md says so.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

LOWER_IS_BETTER = {"deaths", "critical_care_mean", "serious_care_mean", "response_mean",
                   "overload_min", "er_wait_over_base", "unserved_calls", "not_in_care_end",
                   "rejections", "capacity_failures", "escalations", "fallback_rate"}
SHOWN = ["deaths", "outcome_score", "critical_on_time", "critical_care_mean",
         "serious_care_mean", "response_mean", "overload_min", "er_wait_over_base",
         "unserved_calls", "not_in_care_end", "capacity_failures", "rejections", "escalations",
         "fallback_rate", "llm_calls", "llm_tokens"]
ORDER = ["nearest", "rule_based", "agents_no_negotiation", "agents"]


def flatten(record: dict) -> dict:
    m = record["metrics"]
    tc = m["time_to_care_by_severity"]
    r2 = m["rejections_by_rule"].get("R2", 0)
    return {
        "policy": record["policy"], "backend": record["backend"], "demand": record["demand"],
        "info": record["info"], "seed": record["seed"],
        "deaths": m["deaths"], "outcome_score": m["outcome_score"],
        "critical_on_time": m["critical_on_time_rate"],
        "critical_care_mean": tc["CRITICAL"]["mean"], "serious_care_mean": tc["SERIOUS"]["mean"],
        "response_mean": m["response_time"]["mean"], "overload_min": m["hospital_overload_minutes"],
        "er_wait_over_base": m["ambulance_minutes_at_er_over_base"],
        "unserved_calls": m["unserved_calls_30min"], "not_in_care_end":
        m["patients_not_in_care_at_end"],
        "capacity_failures": r2 + m["patients_not_in_care_at_end"],
        "rejections": sum(m["rejections_by_rule"].values()), "escalations": m["escalations"],
        "fallback_rate": m["fallback_rate"], "llm_calls": m["llm_calls"],
        "llm_tokens": m["llm_tokens"], "wall_seconds": record.get("wall_seconds"),
        "calibration": m.get("confidence_calibration", []),
    }


def load_runs(runs_dir: Path) -> pd.DataFrame:
    rows = [flatten(json.loads(p.read_text())) for p in sorted(runs_dir.glob("*.json"))]
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["policy", "demand", "info"]
    agg = df.groupby(keys)[SHOWN].agg(["mean", "std"])
    agg.columns = [f"{m}_{s}" for m, s in agg.columns]
    agg["runs"] = df.groupby(keys).size()
    return agg.reset_index()


def _fmt(mean, sd) -> str:
    if mean is None or (isinstance(mean, float) and math.isnan(mean)):
        return "—"
    sd_txt = "" if sd is None or (isinstance(sd, float) and math.isnan(sd)) else f" ± {sd:.1f}"
    return f"{mean:.2f}{sd_txt}" if abs(mean) < 10 else f"{mean:.0f}{sd_txt}"


def paired(df: pd.DataFrame, a: str, b: str, metric: str, **cell) -> dict | None:
    """Per-seed improvement of policy a over b (positive = a better)."""
    sub = df
    for k, v in cell.items():
        sub = sub[sub[k] == v]
    pa = sub[sub.policy == a].set_index(["demand", "info", "seed"])[metric]
    pb = sub[sub.policy == b].set_index(["demand", "info", "seed"])[metric]
    joined = pd.concat([pa, pb], axis=1, keys=["a", "b"]).dropna()
    if joined.empty:
        return None
    diff = joined["b"] - joined["a"] if metric in LOWER_IS_BETTER else joined["a"] - joined["b"]
    return {"n": len(diff), "mean": float(diff.mean()), "wins": int((diff > 0).sum()),
            "losses": int((diff < 0).sum())}


def verdict(r: dict | None) -> str:
    if r is None:
        return "not tested yet (runs missing)"
    if r["mean"] > 0 and r["wins"] >= math.ceil(0.8 * r["n"]):
        return "supported"
    if r["mean"] <= 0 and r["wins"] <= math.floor(0.2 * r["n"]):
        return "not supported"
    return "mixed"


def _describe(r: dict | None, metric: str) -> str:
    if r is None:
        return f"{metric}: no paired runs yet"
    better = "lower" if metric in LOWER_IS_BETTER else "higher"
    return (f"{metric}: mean improvement {r['mean']:+.2f} ({better} is better); better in "
            f"{r['wins']}/{r['n']} paired runs, worse in {r['losses']}")


def hypotheses(df: pd.DataFrame) -> list[str]:
    lines = ["## Hypotheses", "",
             "Paired comparisons on identical scenarios (same seed). With few seeds this is "
             "descriptive evidence, not a significance test.", ""]
    h1 = [paired(df, "agents", "agents_no_negotiation", m) for m in ("capacity_failures",
                                                                      "overload_min")]
    lines += ["**H1. Negotiation reduces unresolved conflicts and capacity-related failures** "
              "(agents vs agents without negotiation, all cells).",
              f"- Verdict: {verdict(h1[0])}",
              f"- {_describe(h1[0], 'capacity_failures')}",
              f"- {_describe(h1[1], 'overload_min')}", ""]
    best = []
    for b in ("rule_based", "agents_no_negotiation"):
        best.append((b, paired(df, "agents", b, "critical_care_mean", demand="surge"),
                     paired(df, "agents", b, "critical_on_time", demand="surge")))
    lines += ["**H2. Negotiation improves time to definitive care for critical patients during "
              "scarcity** (surge cells)."]
    for b, care, on_time in best:
        lines += [f"- vs {b}: verdict {verdict(care)}; {_describe(care, 'critical_care_mean')}; "
                  f"{_describe(on_time, 'critical_on_time')}"]
    lines.append("")
    lines += ["**H3. The benefit is larger under surge and partial information** (agents vs "
              "rule_based, outcome score)."]
    cells = {}
    for d in ("normal", "surge"):
        for i in ("complete", "partial"):
            cells[(d, i)] = paired(df, "agents", "rule_based", "outcome_score", demand=d, info=i)
    for (d, i), r in cells.items():
        lines.append(f"- {d} / {i}: {_describe(r, 'outcome_score')}")
    have = {k: v["mean"] for k, v in cells.items() if v}
    if len(have) == 4:
        surge_gain = (have[("surge", "complete")] + have[("surge", "partial")]) / 2
        normal_gain = (have[("normal", "complete")] + have[("normal", "partial")]) / 2
        partial_gain = (have[("normal", "partial")] + have[("surge", "partial")]) / 2
        complete_gain = (have[("normal", "complete")] + have[("surge", "complete")]) / 2
        h3 = surge_gain > normal_gain and partial_gain > complete_gain
        lines.append(f"- Verdict: {'supported' if h3 else 'not supported'} (surge gain "
                     f"{surge_gain:+.2f} vs normal {normal_gain:+.2f}; partial gain "
                     f"{partial_gain:+.2f} vs complete {complete_gain:+.2f})")
    else:
        lines.append("- Verdict: not tested yet (runs missing)")
    return lines + [""]


def write_reports(runs_dir: Path, out_dir: Path) -> list[Path]:
    df = load_runs(runs_dir)
    if df.empty:
        return []
    summary = summarize(df)
    csv = out_dir / "summary.csv"
    summary.to_csv(csv, index=False)

    backends = sorted(set(df.loc[df.backend != "none", "backend"]))
    lines = ["# ORCA-EMS results", "",
             f"{len(df)} runs · seeds {sorted(df.seed.unique().tolist())} · "
             f"policies {sorted(df.policy.unique().tolist(), key=ORDER.index)}", ""]
    if "scripted" in backends:
        lines += ["> **Dry run.** Agent rows here use the deterministic scripted stand-in, not "
                  "an LLM. They test the pipeline and must not be reported as LLM results.", ""]
    if not set(df.policy) & {"agents", "agents_no_negotiation"}:
        lines += ["> LLM agent runs are pending (set OPENAI_API_KEY and OPENAI_MODEL in .env "
                  "and rerun). Only baselines are shown.", ""]
    lines += ["Synthetic simulation; the outcome score is a modeled survival sum, not a "
              "clinical measure. Mean ± standard deviation over seeds.", ""]
    cols = ["deaths", "outcome_score", "critical_on_time", "critical_care_mean",
            "response_mean", "overload_min", "er_wait_over_base", "not_in_care_end",
            "capacity_failures", "escalations", "llm_calls"]
    for demand in ("normal", "surge"):
        for info in ("complete", "partial"):
            cell = summary[(summary["demand"] == demand) & (summary["info"] == info)]
            if cell.empty:
                continue
            lines += [f"### {demand.title()} demand · {info} information", "",
                      "| policy | " + " | ".join(cols) + " |",
                      "|---" * (len(cols) + 1) + "|"]
            for pol in sorted(cell.policy, key=ORDER.index):
                row = cell[cell.policy == pol].iloc[0]
                lines.append(f"| {pol} | " + " | ".join(
                    _fmt(row[f"{c}_mean"], row[f"{c}_std"]) for c in cols) + " |")
            lines.append("")
    lines += hypotheses(df)

    cal = [c for cs in df["calibration"] for c in cs]
    lines += ["## Confidence calibration (agents)", ""]
    if cal:
        cdf = pd.DataFrame(cal)
        cdf["matched"] = cdf["matched_hindsight_best"] * cdf["decisions"]
        g = cdf.groupby("bin")[["decisions", "matched"]].sum()
        lines += ["| confidence bin | decisions | matched hindsight-best |", "|---|---|---|"]
        for b, r in g.iterrows():
            lines.append(f"| {b} | {int(r.decisions)} | {r.matched / r.decisions:.0%} |")
    else:
        lines.append("No agent decisions with confidence scores yet.")
    lines += ["", "## Cost per run", "", "| policy | LLM calls | tokens | wall seconds |",
              "|---|---|---|---|"]
    for pol, g in sorted(df.groupby("policy"), key=lambda kv: ORDER.index(kv[0])):
        lines.append(f"| {pol} | {g.llm_calls.mean():.0f} | {g.llm_tokens.mean():.0f} | "
                     f"{g.wall_seconds.mean():.1f} |")
    md = out_dir / "summary.md"
    md.write_text("\n".join(lines) + "\n")
    return [csv, md]
