"""Dashboard state built only from the event log up to a tick.

The same code serves live mode (the running engine's log) and replay (a saved JSONL file), and
it has no Streamlit dependency so it can be tested directly.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from eval.handling import SEVERITY_ORDER, call_handling
from sim.events import Event, EventType

# Feed categories drive colors in the UI.
CALL, AGENT, DECISION, REJECT, FLAG, UNIT, HOSPITAL, PATIENT, ALERT = (
    "call", "agent", "decision", "reject", "flag", "unit", "hospital", "patient", "alert")

AT_INCIDENT = {"EN_ROUTE", "STAGING", "ON_SCENE", "LOADING"}
AT_HOSPITAL = {"TRANSPORTING", "WAITING_AT_ER", "HANDOVER"}
THREAD_UNIT_STATES = {"EN_ROUTE", "STAGING", "ON_SCENE", "LOADING", "TRANSPORTING",
                      "WAITING_AT_ER"}
PATIENT_TEXT = {
    "IN_TRANSPORT": "loaded into ambulance",
    "WAITING_AT_ER": "arrived at hospital, waiting for a bed",
    "IN_TREATMENT": "in definitive care",
    "DISCHARGED": "discharged",
    "DECEASED": "died before definitive care",
}


@dataclass
class FeedRow:
    tick: int
    sender: str
    recipient: str
    kind: str  # short label, e.g. "911 CALL", "PROPOSE", "REJECTED R2"
    text: str
    category: str
    incident_id: str | None = None


@dataclass
class DashState:
    tick: int
    run: dict[str, Any]
    hospitals: dict[str, dict[str, Any]]
    hospital_changes: dict[str, list[str]]
    units: dict[str, dict[str, Any]]
    incidents: dict[str, dict[str, Any]]
    threads: dict[str, list[FeedRow]]
    feed: list[FeedRow]
    handling: list[dict[str, Any]]
    kpis: dict[str, Any] = field(default_factory=dict)


def _hospital_name(hid: str | None) -> str:
    return f"Hospital {hid}" if hid else "?"


def _action_text(action: dict[str, Any]) -> str:
    kind = action.get("kind")
    if kind == "dispatch":
        who = ", ".join(action.get("patient_ids") or []) or "crew triage on scene"
        dest = f", then {_hospital_name(action['target_hospital'])}" \
            if action.get("target_hospital") else ""
        return f"send {action['unit_id']} to {action['incident_id']} for {who}{dest}"
    if kind == "route":
        return f"{action['unit_id']} transports to {_hospital_name(action['hospital_id'])}"
    if kind == "lend_staff":
        return (f"Hospital {action['lender_id']} lends {action['nurses']} nurse(s) to "
                f"Hospital {action['borrower_id']}")
    if kind == "mutual_aid":
        return f"activate {action['units']} unit(s) from {action['firm_id']}"
    return str(action)


def build_state(events: list[Event], upto: int | None = None) -> DashState:
    events = [e for e in events if upto is None or e.tick <= upto]
    tick = upto if upto is not None else (events[-1].tick if events else 0)
    started = next((e.payload for e in events if e.type == EventType.RUN_STARTED), {})
    hospital_cfg = {h["id"]: h for h in started.get("hospitals", [])}
    incident_cfg = {i["id"]: i for i in started.get("incidents", [])}
    patient_cfg = {p["id"]: p for p in started.get("patients", [])}
    homes = {a["id"]: a["home_station"] for a in started.get("ambulances", [])}

    hospitals: dict[str, dict[str, Any]] = {}
    changes: dict[str, list[str]] = defaultdict(list)
    units: dict[str, dict[str, Any]] = {
        uid: {"id": uid, "kind": "AMBULANCE", "state": "IDLE", "incident_id": None,
              "hospital_id": None, "location": loc, "activated": not uid.startswith("PVT")}
        for uid, loc in homes.items()
    }
    incidents: dict[str, dict[str, Any]] = {}
    threads: dict[str, list[FeedRow]] = defaultdict(list)
    feed: list[FeedRow] = []
    patient_status: dict[str, str] = {}
    patient_unit: dict[str, str] = {}
    unit_incident: dict[str, str] = {}

    def add(row: FeedRow, to_feed: bool = True) -> None:
        if to_feed:
            feed.append(row)
        if row.incident_id:
            threads[row.incident_id].append(row)

    for e in events:
        p = e.payload
        t = e.type
        if t == EventType.CALL_RECEIVED:
            cfg = incident_cfg.get(p["incident_id"], {})
            incidents[p["incident_id"]] = {
                "id": p["incident_id"], "type": p["type"], "call_tick": e.tick,
                "location": p["location"], "reported": p["reported_victims"],
                "victims": cfg.get("victims", p["reported_victims"]), "violent": p["violent"],
                "secured": not p["violent"], "narrative": p["narrative"],
            }
            add(FeedRow(e.tick, "caller", "dispatch", "911 CALL",
                        f"{p['type'].replace('_', ' ').title()}, reported {p['reported_victims']}"
                        f" victim(s): “{p['narrative']}”", CALL, p["incident_id"]))
        elif t == EventType.SCENE_REPORT:
            counts = ", ".join(f"{p['by_severity'][s]} {s.lower()}" for s in SEVERITY_ORDER
                               if p["by_severity"].get(s))
            add(FeedRow(e.tick, e.actor, "dispatch", "SCENE REPORT",
                        f"{p['victims']} victim(s) on scene: {counts}", UNIT, p["incident_id"]))
        elif t == EventType.SCENE_SECURED:
            if p["incident_id"] in incidents:
                incidents[p["incident_id"]]["secured"] = True
            add(FeedRow(e.tick, e.actor, "all", "SCENE SECURED",
                        "police report the scene is safe; staged units move in", ALERT,
                        p["incident_id"]))
        elif t == EventType.COMMITTED:
            action = p["action"]
            inc = action.get("incident_id")
            if action.get("kind") == "dispatch":
                unit_incident[action["unit_id"]] = inc
            inc = inc or unit_incident.get(action.get("unit_id", ""))
            add(FeedRow(e.tick, e.actor, "engine", "COMMITTED", _action_text(action), DECISION,
                        inc))
        elif t == EventType.PROPOSAL_VALIDATED and p.get("flags"):
            action = p["action"]
            inc = action.get("incident_id") or unit_incident.get(action.get("unit_id", ""))
            for f in p["flags"]:
                label = "NEEDS REVIEW" if f["level"] == "review" else "WARNING"
                add(FeedRow(e.tick, "validator", e.actor, f"{label} {f['rule_id']}",
                            f"{f['code']}: {f['reason']}", FLAG, inc))
        elif t == EventType.PROPOSAL_REJECTED:
            action = p.get("action") or {}
            inc = action.get("incident_id") or unit_incident.get(action.get("unit_id", ""))
            what = _action_text(action) if action else "policy action"
            add(FeedRow(e.tick, "validator", e.actor, f"REJECTED {p['rule_id']}",
                        f"{p.get('code', '')}: {what}. {p.get('reason', '')}".strip(), REJECT,
                        inc))
        elif t == EventType.MESSAGE:
            category = HOSPITAL if p["sender"].startswith("hospital") else AGENT
            add(FeedRow(e.tick, p["sender"], p["recipient"], p["type"].replace("_", " "),
                        p.get("reason", ""), category, p.get("incident_id")))
        elif t == EventType.STAFF_LOAN:
            add(FeedRow(e.tick, f"hospital:{p['lender']}", f"hospital:{p['borrower']}",
                        f"STAFF {p['phase']}", f"{p['nurses']} nurse(s)", HOSPITAL))
        elif t == EventType.WALK_IN:
            add(FeedRow(e.tick, p["patient_id"], f"hospital:{p['hospital_id']}", "WALK-IN",
                        "patient arrived without an ambulance", PATIENT, p["incident_id"]))
        elif t == EventType.UNIT_STATE_CHANGED:
            uid = p["unit_id"]
            if p.get("kind") != "AMBULANCE":
                continue
            u = units.setdefault(uid, {"id": uid, "kind": "AMBULANCE", "location": None,
                                       "activated": True})
            u["state"] = p["to"]
            if p.get("incident_id"):
                u["incident_id"] = p["incident_id"]
            if p.get("hospital_id"):
                u["hospital_id"] = p["hospital_id"]
            if p["to"] in ("RETURNING", "IDLE"):
                u["incident_id"], u["hospital_id"] = None, None
            inc = p.get("incident_id") or unit_incident.get(uid)
            if p["to"] in THREAD_UNIT_STATES and inc:
                where = f" to {_hospital_name(p.get('hospital_id'))}" \
                    if p["to"] == "TRANSPORTING" else ""
                add(FeedRow(e.tick, uid, "dispatch", p["to"].replace("_", " "),
                            f"{uid} {p['to'].lower().replace('_', ' ')}{where}", UNIT, inc),
                    to_feed=False)
        elif t == EventType.PATIENT_STATE_CHANGED:
            pid = p["patient_id"]
            patient_status[pid] = p["to"]
            if p.get("unit_id"):
                patient_unit[pid] = p["unit_id"]
            inc = patient_cfg.get(pid, {}).get("incident_id")
            where = f" at {_hospital_name(p.get('hospital_id'))}" if p.get("hospital_id") else ""
            text = f"{pid} {PATIENT_TEXT.get(p['to'], p['to'].lower())}{where}"
            if p["to"] == "IN_TREATMENT" and p.get("stabilization_only"):
                text += " (stabilization only)"
            add(FeedRow(e.tick, "engine", "all", p["to"].replace("_", " "), text, PATIENT, inc),
                to_feed=p["to"] in ("IN_TREATMENT", "DECEASED"))
            if p["to"] == "IN_TREATMENT" and p.get("hospital_id"):
                via = f" via {patient_unit[pid]}" if pid in patient_unit else ""
                changes[p["hospital_id"]].append(f"t={e.tick}: admitted {pid}{via}")
            if p["to"] == "DISCHARGED" and p.get("hospital_id"):
                changes[p["hospital_id"]].append(f"t={e.tick}: discharged {pid}")
        elif t == EventType.HOSPITAL_STATUS:
            hospitals[p["hospital_id"]] = dict(p)
        elif t == EventType.MONITOR_ALERT:
            add(FeedRow(e.tick, "monitor", "all", "ALERT", str(p.get("message", p)), ALERT,
                        p.get("incident_id")))
        elif t in (EventType.ESCALATED, EventType.APPROVED, EventType.OVERRIDDEN,
                   EventType.FALLBACK_USED, EventType.PRIORITY_REPORT):
            add(FeedRow(e.tick, e.actor, str(p.get("recipient", "all")), t.value.replace("_", " "),
                        str(p.get("reason", "")), AGENT, p.get("incident_id")))

    for hid, cfg in hospital_cfg.items():
        if hid in hospitals:
            hospitals[hid]["name"] = cfg["name"]
            hospitals[hid]["location"] = cfg["location"]
            hospitals[hid]["owner"] = cfg["owner"]
            hospitals[hid]["stabilization_only"] = cfg.get("stabilization_only", False)

    for u in units.values():  # logical place on the map (no live tracking)
        if u["state"] in AT_INCIDENT and u.get("incident_id") in incidents:
            u["location"] = incidents[u["incident_id"]]["location"]
        elif u["state"] in AT_HOSPITAL and u.get("hospital_id") in hospital_cfg:
            u["location"] = hospital_cfg[u["hospital_id"]]["location"]
        elif u["id"] in homes:
            u["location"] = homes[u["id"]]
    for msg in feed:
        if msg.kind == "STATUS" and "units activated" in msg.text:
            for uid in units:
                if uid in msg.text:
                    units[uid]["activated"] = True

    for inc in incidents.values():
        pids = [pid for pid, cfg in patient_cfg.items() if cfg["incident_id"] == inc["id"]]
        inc["waiting"] = sum(1 for pid in pids
                             if patient_status.get(pid, "WAITING_ON_SCENE") == "WAITING_ON_SCENE")
        inc["severities"] = sorted({patient_cfg[pid]["severity"] for pid in pids})

    called = {pid for pid, cfg in patient_cfg.items() if cfg["incident_id"] in incidents}
    status_counts = defaultdict(int)
    for pid in called:
        status_counts[patient_status.get(pid, "WAITING_ON_SCENE")] += 1
    handling = call_handling(events)
    care = [r["care_mean_min"] for r in handling if r["care_mean_min"] is not None]
    active_units = [u for u in units.values() if u.get("activated")]
    kpis = {
        "calls": len(incidents),
        "waiting_on_scene": status_counts["WAITING_ON_SCENE"],
        "in_transport": status_counts["IN_TRANSPORT"],
        "waiting_at_er": status_counts["WAITING_AT_ER"],
        "in_care": status_counts["IN_TREATMENT"] + status_counts["DISCHARGED"],
        "deceased": status_counts["DECEASED"],
        "free_units": sum(1 for u in active_units if u["state"] == "IDLE"),
        "units": len(active_units),
        "boarding": sum(h.get("boarding", 0) for h in hospitals.values()),
        "avg_call_to_care": round(sum(care) / len(care), 1) if care else None,
    }
    return DashState(tick=tick, run=started, hospitals=hospitals,
                     hospital_changes=dict(changes), units=units, incidents=incidents,
                     threads=dict(threads), feed=feed, handling=handling, kpis=kpis)
