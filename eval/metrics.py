"""Run metrics (PLAN §16), computed only from the event log.

All times are simulated minutes. The outcome score is a synthetic model (`sim/outcomes.py`),
not a clinical measure.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from statistics import mean, median
from typing import Any

from eval.handling import SEVERITY_ORDER
from sim.events import Event, EventType

ON_TIME_MIN = 60  # modeled critical threshold
UNSERVED_MIN = 30
BASE_HANDOVER_MIN = 10
NEGOTIATION_TYPES = (
    "PROPOSE",
    "ACCEPT",
    "REJECT",
    "COUNTER",
    "ESCALATE",
    "RESOLVE",
    "STAFF_REQUEST",
    "STAFF_RESPONSE",
    "MUTUAL_AID_REQUEST",
)


def _stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "mean": None, "median": None, "p90": None}
    s = sorted(values)
    p90 = s[min(len(s) - 1, int(round(0.9 * (len(s) - 1))))]
    return {
        "n": len(s),
        "mean": round(mean(s), 1),
        "median": round(median(s), 1),
        "p90": round(p90, 1),
    }


def compute_metrics(events: Iterable[Event]) -> dict[str, Any]:
    events = list(events)
    started = next(e for e in events if e.type == EventType.RUN_STARTED).payload
    end_tick = events[-1].tick
    patients = {p["id"]: p for p in started["patients"]}
    incidents = {i["id"]: i for i in started["incidents"]}

    call_tick: dict[str, int] = {}
    first_on_scene: dict[str, int] = {}
    care_tick: dict[str, int] = {}
    stabilization: set[str] = set()
    status: dict[str, str] = {}
    unit_state: dict[str, tuple[str, int]] = {}
    er_minutes_over = 0.0
    hospital_status: dict[str, list[tuple[int, bool]]] = defaultdict(list)
    rejections: Counter = Counter()
    messages: Counter = Counter()
    rounds: list[int] = []
    counts: Counter = Counter()
    llm = []
    confidence = []

    def close_unit(uid: str, tick: int) -> None:
        nonlocal er_minutes_over
        prev = unit_state.get(uid)
        if prev and prev[0] == "WAITING_AT_ER":
            er_minutes_over += max(0, tick - prev[1] - BASE_HANDOVER_MIN)

    for e in events:
        p = e.payload
        if e.type == EventType.CALL_RECEIVED:
            call_tick[p["incident_id"]] = e.tick
        elif e.type == EventType.UNIT_STATE_CHANGED and p.get("kind") == "AMBULANCE":
            close_unit(p["unit_id"], e.tick)
            unit_state[p["unit_id"]] = (p["to"], e.tick)
            if p["to"] == "ON_SCENE" and p.get("incident_id"):
                first_on_scene.setdefault(p["incident_id"], e.tick)
        elif e.type == EventType.PATIENT_STATE_CHANGED:
            status[p["patient_id"]] = p["to"]
            if p["to"] == "IN_TREATMENT":
                if p.get("stabilization_only"):
                    stabilization.add(p["patient_id"])
                else:
                    care_tick.setdefault(p["patient_id"], e.tick)
        elif e.type == EventType.HOSPITAL_STATUS:
            overloaded = p["er_occupancy"] >= 1.0 or p.get("queue_scenario", 0) > 0
            hospital_status[p["hospital_id"]].append((e.tick, overloaded))
        elif e.type == EventType.PROPOSAL_REJECTED:
            rejections[p["rule_id"]] += 1
        elif e.type == EventType.MESSAGE:
            messages[p["type"]] += 1
            if p["type"] in ("ACCEPT", "RESOLVE"):
                rounds.append(p.get("negotiation_round", 0))
        elif e.type == EventType.LLM_CALL:
            llm.append(p)
        elif e.type in (
            EventType.ESCALATED,
            EventType.APPROVED,
            EventType.OVERRIDDEN,
            EventType.FALLBACK_USED,
            EventType.COMMITTED,
            EventType.PROPOSAL_VALIDATED,
        ):
            counts[e.type.value] += 1
            if p.get("confidence") is not None:
                confidence.append(p)
    for uid in unit_state:
        close_unit(uid, end_tick)

    # Response time per call (first unit on scene), split by the call's worst severity.
    by_inc_sev: dict[str, str] = {}
    for pt in patients.values():
        cur = by_inc_sev.get(pt["incident_id"])
        if cur is None or SEVERITY_ORDER.index(pt["severity"]) < SEVERITY_ORDER.index(cur):
            by_inc_sev[pt["incident_id"]] = pt["severity"]
    response = {
        iid: first_on_scene[iid] - t for iid, t in call_tick.items() if iid in first_on_scene
    }
    response_by_sev = {
        s: _stats([v for iid, v in response.items() if by_inc_sev.get(iid) == s])
        for s in SEVERITY_ORDER
    }

    called = {pid: pt for pid, pt in patients.items() if pt["incident_id"] in call_tick}
    care = {pid: care_tick[pid] - pt["call_tick"] for pid, pt in called.items() if pid in care_tick}
    care_by_sev = {
        s: _stats([v for pid, v in care.items() if called[pid]["severity"] == s])
        for s in SEVERITY_ORDER
    }
    # Stabilization is not definitive care. Keep those patients in the denominator so
    # sending a critical patient to stabilization cannot improve the success rate.
    critical = [pid for pid, pt in called.items() if pt["severity"] == "CRITICAL"]
    on_time = sum(1 for pid in critical if pid in care and care[pid] <= ON_TIME_MIN)

    overload = 0
    for series in hospital_status.values():
        for (t0, over), (t1, _) in zip(series, series[1:] + [(end_tick, False)], strict=True):
            overload += (t1 - t0) if over else 0

    unserved_calls = sum(
        1
        for iid, t in call_tick.items()
        if first_on_scene.get(iid, end_tick + 1) - t > UNSERVED_MIN
    )
    not_in_care = sum(
        1
        for pid in called
        if status.get(pid, "WAITING_ON_SCENE")
        in ("WAITING_ON_SCENE", "IN_TRANSPORT", "WAITING_AT_ER")
        or (pid in stabilization and pid not in care_tick and status.get(pid) != "DECEASED")
    )
    summary = next((e.payload for e in events if e.type == EventType.RUN_SUMMARY), None)
    outcome = None
    if summary:
        outcome = round(
            sum(p["survival_prob"] or 0.0 for p in summary["patients"] if p["id"] in called), 3
        )

    decisions = counts["PROPOSAL_VALIDATED"] + sum(rejections.values())
    return {
        "calls": len(call_tick),
        "patients": len(called),
        "response_time": _stats(list(response.values())),
        "response_time_by_severity": response_by_sev,
        "time_to_care_by_severity": care_by_sev,
        "critical_on_time_rate": round(on_time / len(critical), 3) if critical else None,
        "critical_patients": len(critical),
        "stabilization_only_admissions": len(stabilization),
        "hospital_overload_minutes": overload,
        "ambulance_minutes_at_er_over_base": er_minutes_over,
        "unserved_calls_30min": unserved_calls,
        "patients_not_in_care_at_end": not_in_care,
        "deaths": sum(1 for pid in called if status.get(pid) == "DECEASED"),
        "outcome_score": outcome,
        "negotiation": {t: messages[t] for t in NEGOTIATION_TYPES if messages[t]},
        "mean_rounds_per_resolution": round(mean(rounds), 2) if rounds else None,
        "rejections_by_rule": dict(sorted(rejections.items())),
        "escalations": counts["ESCALATED"],
        "approvals": counts["APPROVED"],
        "overrides": counts["OVERRIDDEN"],
        "fallbacks": counts["FALLBACK_USED"],
        "fallback_rate": round(counts["FALLBACK_USED"] / decisions, 3) if decisions else 0.0,
        "confidence_calibration": confidence_calibration(confidence),
        "llm_calls": len(llm),
        "llm_tokens": sum(c.get("tokens", 0) for c in llm),
        "llm_latency_ms": round(sum(c.get("latency_ms", 0) for c in llm), 1),
        "llm_cache_hit_rate": round(sum(1 for c in llm if c.get("cache_hit")) / len(llm), 3)
        if llm
        else None,
        "incidents": len(incidents),
    }


def confidence_calibration(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For decisions in each confidence bin, the share that matched the hindsight-best option."""
    bins = [(0.0, 0.75), (0.75, 0.9), (0.9, 1.01)]
    out = []
    for lo, hi in bins:
        rows = [r for r in records if lo <= r["confidence"] < hi and "hindsight_best" in r]
        if rows:
            out.append(
                {
                    "bin": f"{lo:.2f}-{min(hi, 1.0):.2f}",
                    "decisions": len(rows),
                    "matched_hindsight_best": round(
                        sum(1 for r in rows if r["hindsight_best"]) / len(rows), 3
                    ),
                }
            )
    return out


def headline(m: dict[str, Any]) -> dict[str, Any]:
    """The few numbers shown in tables and the CLI."""
    crit = m["time_to_care_by_severity"]["CRITICAL"]
    return {
        "deaths": m["deaths"],
        "outcome_score": m["outcome_score"],
        "critical_on_time": m["critical_on_time_rate"],
        "critical_care_mean": crit["mean"],
        "response_mean": m["response_time"]["mean"],
        "overload_min": m["hospital_overload_minutes"],
        "er_wait_over_base": m["ambulance_minutes_at_er_over_base"],
        "unserved_calls": m["unserved_calls_30min"],
        "not_in_care_end": m["patients_not_in_care_at_end"],
        "rejections": sum(m["rejections_by_rule"].values()),
        "escalations": m["escalations"],
        "fallback_rate": m["fallback_rate"],
        "llm_calls": m["llm_calls"],
        "llm_tokens": m["llm_tokens"],
    }
