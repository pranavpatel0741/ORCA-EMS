"""How long the system takes to handle each call, computed only from the event log.

Simulated minutes, measured from the call:
- decision: first committed dispatch for the call
- scene: first ambulance on scene
- hospital: first patient arrives at a hospital (ambulance or walk-in)
- care: each patient reaches definitive care (mean and max over the call's patients)

Real (wall-clock) decision time is not in the deterministic log. It comes from
`Engine.decision_timings` and, once agents exist, from `LLM_CALL` events.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from statistics import mean
from typing import Any

from sim.events import Event, EventType

SEVERITY_ORDER = ["CRITICAL", "SERIOUS", "MINOR", "EXPECTANT"]


def _patients(events: list[Event]) -> dict[str, dict[str, Any]]:
    started = next((e for e in events if e.type == EventType.RUN_STARTED), None)
    return {p["id"]: p for p in started.payload["patients"]} if started else {}


def call_handling(events: Iterable[Event]) -> list[dict[str, Any]]:
    """One row per call received so far."""
    events = list(events)
    patients = _patients(events)
    by_incident: dict[str, list[str]] = defaultdict(list)
    for pid, p in patients.items():
        by_incident[p["incident_id"]].append(pid)

    rows: dict[str, dict[str, Any]] = {}
    unit_incident: dict[str, str] = {}
    for e in events:
        p = e.payload
        if e.type == EventType.CALL_RECEIVED:
            rows[p["incident_id"]] = {
                "incident_id": p["incident_id"], "type": p["type"], "call_tick": e.tick,
                "victims": len(by_incident[p["incident_id"]]), "reported": p["reported_victims"],
                "decision_min": None, "scene_min": None, "hospital_min": None,
                "care": {}, "deceased": 0, "rejections": 0, "rounds": 0, "messages": 0,
            }
            continue
        if e.type == EventType.COMMITTED and p["action"].get("kind") == "dispatch":
            inc = p["action"]["incident_id"]
            unit_incident[p["action"]["unit_id"]] = inc
            row = rows.get(inc)
            if row and row["decision_min"] is None:
                row["decision_min"] = e.tick - row["call_tick"]
        elif e.type == EventType.PROPOSAL_REJECTED:
            action = p.get("action") or {}
            inc = action.get("incident_id") or unit_incident.get(action.get("unit_id", ""))
            if inc in rows:
                rows[inc]["rejections"] += 1
        elif e.type == EventType.UNIT_STATE_CHANGED and p.get("kind") == "AMBULANCE" \
                and p.get("to") == "ON_SCENE":
            row = rows.get(p.get("incident_id"))
            if row and row["scene_min"] is None:
                row["scene_min"] = e.tick - row["call_tick"]
        elif e.type == EventType.PATIENT_STATE_CHANGED:
            inc = patients.get(p["patient_id"], {}).get("incident_id")
            row = rows.get(inc)
            if row is None:
                continue
            if p["to"] == "WAITING_AT_ER" and row["hospital_min"] is None:
                row["hospital_min"] = e.tick - row["call_tick"]
            elif p["to"] == "IN_TREATMENT":
                row["care"][p["patient_id"]] = e.tick - row["call_tick"]
            elif p["to"] == "DECEASED":
                row["deceased"] += 1
        elif e.type == EventType.MESSAGE:
            row = rows.get(p.get("incident_id"))
            if row:
                row["messages"] += 1
                row["rounds"] = max(row["rounds"], p.get("negotiation_round", 0))

    out = []
    for row in rows.values():
        care = list(row.pop("care").values())
        row["in_care"] = len(care)
        row["care_mean_min"] = round(mean(care), 1) if care else None
        row["care_max_min"] = max(care) if care else None
        out.append(row)
    return sorted(out, key=lambda r: (r["call_tick"], r["incident_id"]))


def patient_handling(events: Iterable[Event]) -> list[dict[str, Any]]:
    """Call → definitive care per patient (None while not yet in care)."""
    events = list(events)
    patients = _patients(events)
    care: dict[str, int] = {}
    deceased: set[str] = set()
    called = {e.payload["incident_id"] for e in events if e.type == EventType.CALL_RECEIVED}
    for e in events:
        if e.type == EventType.PATIENT_STATE_CHANGED:
            if e.payload["to"] == "IN_TREATMENT":
                care.setdefault(e.payload["patient_id"], e.tick)
            elif e.payload["to"] == "DECEASED":
                deceased.add(e.payload["patient_id"])
    rows = []
    for pid, p in sorted(patients.items()):
        if p["incident_id"] not in called:
            continue
        rows.append({"patient_id": pid, "incident_id": p["incident_id"], "severity": p["severity"],
                     "care_min": care[pid] - p["call_tick"] if pid in care else None,
                     "deceased": pid in deceased})
    return rows


def by_severity(patient_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for sev in SEVERITY_ORDER:
        rows = [r for r in patient_rows if r["severity"] == sev]
        if not rows:
            continue
        times = [r["care_min"] for r in rows if r["care_min"] is not None]
        out.append({"severity": sev, "patients": len(rows), "in_care": len(times),
                    "care_mean_min": round(mean(times), 1) if times else None,
                    "care_max_min": max(times) if times else None,
                    "deceased": sum(r["deceased"] for r in rows)})
    return out


def decision_time(timings: list[dict[str, Any]], events: Iterable[Event] = ()) -> dict[str, Any]:
    """Real time spent deciding: policy wall-clock plus LLM usage once agents exist."""
    llm = [e.payload for e in events if e.type == EventType.LLM_CALL]
    busy = [t for t in timings if t["actions"]]
    return {
        "decisions": len(busy),
        "total_ms": round(sum(t["ms"] for t in timings), 1),
        "mean_ms_per_decision": round(mean(t["ms"] for t in busy), 2) if busy else 0.0,
        "llm_calls": len(llm),
        "tokens": sum(p.get("tokens", 0) for p in llm),
        "llm_latency_ms": round(sum(p.get("latency_ms", 0) for p in llm), 1),
        "cache_hits": sum(1 for p in llm if p.get("cache_hit")),
    }
