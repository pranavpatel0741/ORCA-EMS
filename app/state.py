"""Dashboard state built only from the event log up to a tick.

The same code serves live mode (the running engine's log) and replay (a saved JSONL file), and
it has no Streamlit dependency so it can be tested directly.

Messages are rewritten as plain, radio-style lines between roles (911 caller, Dispatch,
ambulances, hospitals, safety rules, police, fire). Agent messages (PROPOSE / ACCEPT / COUNTER /
RESOLVE) arrive as protocol `MESSAGE` events and show up in the same conversation.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from eval.handling import SEVERITY_ORDER, call_handling
from sim.events import Event, EventType
from sim.town import TownProfile

# Message categories (drive colors) and sender roles (drive the avatar).
CALL, AGENT, DECISION, REJECT, FLAG, UNIT, HOSPITAL, PATIENT, ALERT = (
    "call", "agent", "decision", "reject", "flag", "unit", "hospital", "patient", "alert")

TRIAGE = {"CRITICAL": "RED", "SERIOUS": "YELLOW", "MINOR": "GREEN", "EXPECTANT": "BLACK"}
AT_INCIDENT = {"EN_ROUTE", "STAGING", "ON_SCENE", "LOADING"}
AT_HOSPITAL = {"TRANSPORTING", "WAITING_AT_ER", "HANDOVER"}

UNIT_SAYS = {
    "EN_ROUTE": "Responding.",
    "STAGING": "Staging nearby, waiting for police to secure the scene.",
    "ON_SCENE": "On scene, assessing patients.",
    "LOADING": "Loading patient(s).",
    "TRANSPORTING": "Transporting to {hospital}.",
    "WAITING_AT_ER": "Arrived at {hospital}, waiting to hand over the patient.",
    "HANDOVER": "Handing over to {hospital} staff.",
    "RETURNING": "Clear, returning to station.",
}

# Plain-language explanations of validator codes (shown to people, not to policies).
RULE_TEXT = {
    "UNKNOWN_UNIT": "that unit does not exist",
    "ALREADY_COMMITTED": "{unit} was already given an order this minute",
    "DUPLICATE_PATIENT": "the same patient was listed twice",
    "NOT_ASSIGNABLE": "{unit} is busy with patients and cannot be reassigned",
    "NOT_ACTIVATED": "{unit} is not in service (private unit not activated)",
    "INCIDENT_NOT_ACTIVE": "that call is not active",
    "PATIENT_NOT_AT_INCIDENT": "that patient is not at this call",
    "PATIENT_NOT_WAITING": "that patient is no longer waiting on scene",
    "PATIENT_TAKEN": "another ambulance already has that patient",
    "NOT_ROUTABLE": "{unit} cannot be sent to a hospital right now",
    "NO_PATIENTS": "{unit} has no patient to transport",
    "UNKNOWN_HOSPITAL": "that hospital does not exist",
    "TARGET_WITHOUT_PATIENTS": "a hospital was chosen before the patients were known",
    "MISSING_CAPABILITY": "{hospital} cannot treat this kind of patient",
    "NO_CAPACITY_AT_ETA": "{hospital} will not have a free bed and staff when {unit} arrives",
    "NOT_TRAUMA_CENTER": "{hospital} is not a trauma center",
    "STABILIZATION_NOT_MOST_UNSTABLE": "Hospital B's stabilization bay is kept for the most "
                                       "unstable patient",
    "TRAUMA_CENTER_REACHABLE": "a trauma center can still take this patient in time",
    "NO_CONTRACT": "{hospital} has no contract to take ambulance patients",
    "NO_SURGE": "{hospital} only takes ambulance patients during a mass-casualty surge",
    "SEVERITY_NOT_ELIGIBLE": "{hospital}'s contract only covers stable serious patients",
    "TRAUMA_NOT_ACCEPTED": "{hospital}'s contract excludes trauma patients",
    "CONTRACT_LIMIT": "{hospital} has reached its contract limit",
    "MUTUAL_AID_LIMIT": "the private firm's mutual-aid limit is reached",
    "SELF_LOAN": "a hospital cannot lend nurses to itself",
    "BELOW_COVERAGE": "the lending hospital would drop below its minimum nurse staffing",
    "CRITICAL_NOT_ALONE": "a critical patient must ride alone",
    "OVER_CAPACITY": "an ambulance carries at most two patients",
    "UNKNOWN_ACTION": "that action is not allowed",
    "STATE_MUTATED": "the policy tried to change the world directly",
    "PENDING_APPROVAL": "{unit} already has a decision waiting for human review",
}
FLAG_TEXT = {
    "STAGING": "Scene is not secure. {unit} will stage nearby until police clear it.",
    "ALL_FULL": "Every capable hospital is full. The patient will wait at {hospital}.",
    "OR_LATE": "No operating room is likely free at {hospital} in time.",
}


@dataclass
class FeedRow:
    tick: int
    sender: str
    recipient: str
    kind: str  # short label, e.g. "911 CALL", "ORDER", "BLOCKED"
    text: str
    category: str
    incident_id: str | None = None
    role: str = "system"  # caller | dispatch | unit | hospital | safety | police | fire | firm
    # Who produced it: "ai" (LLM agent), "standin" (offline scripted agent, not AI), "backup"
    # (rule-based backup inside the agent policy), "rules" (a baseline policy), "sim" (the
    # simulation itself: calls, crews, hospitals, safety rules).
    source: str = "sim"
    ai: dict[str, Any] | None = None  # the LLM call behind an "ai" row: model, tokens, ...


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
    patients: dict[str, dict[str, Any]] = field(default_factory=dict)
    kpis: dict[str, Any] = field(default_factory=dict)
    ai_calls: list[dict[str, Any]] = field(default_factory=list)


def _hname(hid: str | None) -> str:
    return f"Hospital {hid}" if hid else "a hospital"


def _role(actor: str) -> str:
    if actor.startswith("hospital"):
        return "hospital"
    if actor.startswith(("AMB", "PVT")):
        return "unit"
    if actor.startswith("POL") or actor == "police":
        return "police"
    if actor.startswith("FIRE"):
        return "fire"
    if actor.startswith("firm"):
        return "firm"
    if actor.startswith("engine") or actor == "validator":
        return "safety"
    return "dispatch"


def _speaker(actor: str) -> str:
    if actor.startswith("hospital:"):
        return _hname(actor.split(":", 1)[1])
    if actor.startswith("firm:"):
        return actor.split(":", 1)[1]
    if actor in ("caller",):
        return "911 caller"
    if actor.startswith("engine") or actor == "validator":
        return "Safety rules"
    if actor == "police":
        return "Police"
    if _role(actor) == "dispatch":
        return "Dispatch"
    return actor


def _action_line(a: dict[str, Any]) -> str:
    if a.get("kind") == "route":
        return f"{a.get('unit_id')} to {_hname(a.get('hospital_id'))}"
    if a.get("kind") == "dispatch":
        return f"{a.get('unit_id')} to {a.get('incident_id')}"
    return a.get("kind", "action")


def hospital_status_label(snapshot: dict[str, Any]) -> str:
    """Board label in the style of hospital status systems (display only)."""
    if snapshot["er_occupancy"] >= 1.0 or snapshot.get("boarding", 0) \
            or snapshot.get("queue_scenario", 0):
        return "SATURATED"
    return "BUSY" if snapshot["er_occupancy"] >= 0.8 else "OPEN"


def build_state(events: list[Event], upto: int | None = None) -> DashState:
    events = [e for e in events if upto is None or e.tick <= upto]
    tick = upto if upto is not None else (events[-1].tick if events else 0)
    started = next((e.payload for e in events if e.type == EventType.RUN_STARTED), {})
    town = TownProfile(population=started.get("population") or 50_000)
    hospital_cfg = {h["id"]: h for h in started.get("hospitals", [])}
    incident_cfg = {i["id"]: i for i in started.get("incidents", [])}
    patient_cfg = {p["id"]: p for p in started.get("patients", [])}
    amb_cfg = {a["id"]: a for a in started.get("ambulances", [])}

    def grid(loc) -> str:
        x, y = town.to_km(*loc)
        return f"grid {x:.0f},{y:.0f}"

    hospitals: dict[str, dict[str, Any]] = {}
    changes: dict[str, list[str]] = defaultdict(list)
    units: dict[str, dict[str, Any]] = {
        uid: {"id": uid, "kind": "AMBULANCE", "unit_type": a["unit_type"], "state": "IDLE",
              "since": 0, "incident_id": None, "hospital_id": None,
              "location": a["home_station"], "home": a["home_station"],
              "activated": a["owner"] == "PUBLIC"}
        for uid, a in amb_cfg.items()
    }
    incidents: dict[str, dict[str, Any]] = {}
    threads: dict[str, list[FeedRow]] = defaultdict(list)
    feed: list[FeedRow] = []
    patients: dict[str, dict[str, Any]] = {
        pid: {"id": pid, "incident_id": p["incident_id"], "severity": p["severity"],
              "triage": TRIAGE[p["severity"]], "status": "WAITING_ON_SCENE",
              "hospital_id": None, "unit_id": None, "walk_in": False}
        for pid, p in patient_cfg.items()
    }
    unit_incident: dict[str, str] = {}
    prealerts: dict[str, str] = {}  # patient -> hospital it is inbound to

    # LLM calls by (minute, agent), so each agent message can show the call that produced it.
    ai_calls = [{"tick": e.tick, **e.payload} for e in events if e.type == EventType.LLM_CALL]
    call_at = {(c["tick"], c["agent"]): c for c in ai_calls}
    ai_source = "standin" if ai_calls and all(c["model"] == "scripted" for c in ai_calls) \
        else "ai"
    decided = Counter()

    def action_source(a: dict[str, Any]) -> str:
        by = a.get("decided_by", "")
        src = ai_source if by == "ai" else "backup" if by == "rules" else "rules"
        decided[src] += 1
        return src

    def add(row: FeedRow) -> None:
        feed.append(row)
        if row.incident_id:
            threads[row.incident_id].append(row)

    def inc_of(action: dict[str, Any]) -> str | None:
        return action.get("incident_id") or unit_incident.get(action.get("unit_id", ""))

    for e in events:
        p, t = e.payload, e.type
        if t == EventType.CALL_RECEIVED:
            iid = p["incident_id"]
            cfg = incident_cfg.get(iid, {})
            incidents[iid] = {
                "id": iid, "type": p["type"], "call_tick": e.tick, "location": p["location"],
                "grid": grid(p["location"]), "reported": p["reported_victims"],
                "victims": cfg.get("victims", p["reported_victims"]), "violent": p["violent"],
                "secured": not p["violent"], "narrative": p["narrative"],
            }
            kind = p["type"].replace("_", " ").lower()
            add(FeedRow(e.tick, "911 caller", "Dispatch", "911 CALL",
                        f"“{p['narrative']}” ({kind}, about {p['reported_victims']} "
                        f"hurt, {grid(p['location'])})", CALL, iid, "caller"))
        elif t == EventType.SCENE_REPORT:
            counts = ", ".join(f"{p['by_severity'][s]} {TRIAGE[s].lower()}"
                               for s in SEVERITY_ORDER if p["by_severity"].get(s))
            add(FeedRow(e.tick, e.actor, "Dispatch", "SCENE REPORT",
                        f"On scene. {p['victims']} patient(s): {counts}.", UNIT,
                        p["incident_id"], "unit"))
        elif t == EventType.SCENE_SECURED:
            if p["incident_id"] in incidents:
                incidents[p["incident_id"]]["secured"] = True
            add(FeedRow(e.tick, "Police", "All units", "SCENE SECURE",
                        "Scene is secure. Units can move in.", ALERT, p["incident_id"],
                        "police"))
        elif t == EventType.COMMITTED:
            a = p["action"]
            if a.get("kind") == "dispatch":
                unit_incident[a["unit_id"]] = a["incident_id"]
                inc = incidents.get(a["incident_id"], {})
                pids = a.get("patient_ids") or []
                crit = sum(1 for x in pids if patient_cfg.get(x, {}).get("severity") == "CRITICAL")
                who = (f"{len(pids)} patient(s)" + (f", {crit} critical" if crit else "")
                       if pids else "patients, triage on arrival")
                dest = f", then transport to {_hname(a['target_hospital'])}" \
                    if a.get("target_hospital") else ""
                kind = inc.get("type", "call").replace("_", " ").lower()
                text = (f"{a['unit_id']}, respond to the {kind} at {inc.get('grid', '')} "
                        f"for {who}{dest}.")
                add(FeedRow(e.tick, "Dispatch", a["unit_id"], "ORDER", text, DECISION,
                            a["incident_id"], "dispatch", action_source(a)))
            elif a.get("kind") == "route":
                add(FeedRow(e.tick, "Dispatch", a["unit_id"], "ORDER",
                            f"{a['unit_id']}, transport to {_hname(a['hospital_id'])}.", DECISION,
                            inc_of(a), "dispatch", action_source(a)))
            elif a.get("kind") == "lend_staff":
                add(FeedRow(e.tick, _hname(a["lender_id"]), _hname(a["borrower_id"]), "STAFF",
                            f"Sending {a['nurses']} nurse(s) to help.", HOSPITAL, None,
                            "hospital", action_source(a)))
            elif a.get("kind") == "mutual_aid":
                add(FeedRow(e.tick, "Dispatch", a["firm_id"], "MUTUAL AID",
                            f"Requesting {a['units']} private ambulance(s).", DECISION, None,
                            "dispatch", action_source(a)))
        elif t == EventType.PROPOSAL_VALIDATED and p.get("flags"):
            a = p["action"]
            for f in p["flags"]:
                fill = {"unit": a.get("unit_id", ""), "hospital": _hname(
                    a.get("target_hospital") or a.get("hospital_id"))}
                if f["level"] == "review":
                    text = f"Needs human review: {f['reason']}."
                    kind = "REVIEW"
                else:
                    text = FLAG_TEXT.get(f["code"], f["reason"]).format(**fill)
                    kind = "CAUTION"
                add(FeedRow(e.tick, "Safety rules", "Dispatch", kind, text, FLAG, inc_of(a),
                            "safety"))
        elif t == EventType.PROPOSAL_REJECTED:
            a = p.get("action") or {}
            fill = {"unit": a.get("unit_id", "the unit"),
                    "hospital": _hname(a.get("target_hospital") or a.get("hospital_id"))}
            why = RULE_TEXT.get(p.get("code", ""), p.get("reason", "")).format(**fill)
            prefix = "Re-check before transport failed" if e.actor == "engine:revalidate" \
                else "Blocked"
            add(FeedRow(e.tick, "Safety rules", "Dispatch", f"BLOCKED {p['rule_id']}",
                        f"{prefix}: {why}.", REJECT, inc_of(a), "safety"))
        elif t == EventType.MESSAGE:
            mtype = p["type"]
            sender, recipient = _speaker(p["sender"]), _speaker(p["recipient"]) \
                if p["recipient"] != "all" else "All"
            text = p.get("reason", "")
            if mtype == "PRE_ALERT":
                sev = (p.get("proposed_action") or {}).get("severities") or []
                tally = {c: sum(1 for s in sev if TRIAGE.get(s) == c) for c in TRIAGE.values()}
                colors = ", ".join(f"{n} {c.lower()}" for c, n in tally.items() if n)
                eta = (p.get("proposed_action") or {}).get("eta_tick", e.tick) - e.tick
                text = f"Inbound with {colors or 'patient(s)'}, ETA {eta} min."
                for pid in p.get("patient_ids", []):
                    prealerts[pid] = p["recipient"].split(":", 1)[-1]
            elif mtype == "STATUS" and (p.get("proposed_action") or {}).get("move"):
                pid = (p.get("patient_ids") or ["?"])[0]
                text = (f"{pid} moved up to a ward bed." if p["proposed_action"]["move"] == "ward"
                        else f"{pid} is boarding in the ER: no ward bed free.")
            category = HOSPITAL if p["sender"].startswith("hospital") else AGENT
            # Agent messages written from an LLM answer in this minute. The confidence check
            # (ESCALATE) and pre-alerts are composed by code, not by an agent.
            call = None if p.get("by_code") or mtype in ("ESCALATE", "PRE_ALERT") \
                else call_at.get((e.tick, p["sender"]))
            add(FeedRow(e.tick, sender, recipient, mtype.replace("_", " "), text, category,
                        p.get("incident_id"), _role(p["sender"]),
                        ai_source if call else "sim", call))
        elif t == EventType.STAFF_LOAN:
            add(FeedRow(e.tick, _hname(p["lender"]), _hname(p["borrower"]),
                        f"STAFF {p['phase']}", f"{p['nurses']} nurse(s) {p['phase'].lower()}.",
                        HOSPITAL, None, "hospital"))
        elif t == EventType.WALK_IN:
            patients.get(p["patient_id"], {}).update(walk_in=True, hospital_id=p["hospital_id"])
            add(FeedRow(e.tick, _hname(p["hospital_id"]), "Dispatch", "WALK-IN",
                        f"{p['patient_id']} from {p['incident_id']} walked in without an "
                        "ambulance.", PATIENT, p["incident_id"], "hospital"))
        elif t == EventType.UNIT_STATE_CHANGED:
            if p.get("kind") != "AMBULANCE":
                continue
            uid = p["unit_id"]
            u = units.setdefault(uid, {"id": uid, "kind": "AMBULANCE", "unit_type": "?",
                                       "location": None, "activated": True})
            u["state"], u["since"] = p["to"], e.tick
            if p.get("incident_id"):
                u["incident_id"] = p["incident_id"]
            if p.get("hospital_id"):
                u["hospital_id"] = p["hospital_id"]
            if p["to"] in ("RETURNING", "IDLE"):
                u["incident_id"], u["hospital_id"] = None, None
            inc = p.get("incident_id") or unit_incident.get(uid)
            if p["to"] in UNIT_SAYS and inc and p["to"] not in ("RETURNING", "LOADING"):
                text = UNIT_SAYS[p["to"]].format(hospital=_hname(p.get("hospital_id")))
                threads[inc].append(FeedRow(e.tick, uid, "Dispatch", p["to"].replace("_", " "),
                                            text, UNIT, inc, "unit"))
        elif t == EventType.PATIENT_STATE_CHANGED:
            pid = p["patient_id"]
            rec = patients.setdefault(pid, {"id": pid, "incident_id": None, "severity": "MINOR",
                                            "triage": "GREEN", "hospital_id": None,
                                            "unit_id": None, "walk_in": False})
            rec["status"] = p["to"]
            if p.get("unit_id"):
                rec["unit_id"] = p["unit_id"]
            if p.get("hospital_id") and p["to"] in ("WAITING_AT_ER", "IN_TREATMENT"):
                rec["hospital_id"] = p["hospital_id"]
            if p["to"] != "IN_TRANSPORT":
                prealerts.pop(pid, None)
            inc = rec["incident_id"]
            if p["to"] == "IN_TREATMENT":
                bay = " (stabilization only)" if p.get("stabilization_only") else ""
                add(FeedRow(e.tick, _hname(p.get("hospital_id")), "Dispatch", "IN CARE",
                            f"{pid} ({rec['triage'].lower()}) is in a treatment bed{bay}.",
                            PATIENT, inc, "hospital"))
                via = f" via {rec['unit_id']}" if rec.get("unit_id") else ""
                changes[p["hospital_id"]].append(f"t={e.tick}: admitted {pid}{via}")
            elif p["to"] == "DECEASED":
                add(FeedRow(e.tick, "Outcome", "All", "DIED",
                            f"{pid} ({rec['triage'].lower()}) died before reaching care.",
                            ALERT, inc, "system"))
            elif p["to"] == "DISCHARGED" and p.get("hospital_id"):
                changes[p["hospital_id"]].append(f"t={e.tick}: discharged {pid}")
        elif t == EventType.HOSPITAL_STATUS:
            hospitals[p["hospital_id"]] = dict(p)
        elif t == EventType.MONITOR_ALERT:
            add(FeedRow(e.tick, "Monitor", "Dispatch",
                        "ALERT" if p.get("phase") == "RAISED" else "ALERT CLEARED",
                        p.get("message", ""), ALERT if p.get("phase") == "RAISED" else UNIT,
                        None, "system"))
        elif t == EventType.ESCALATED:
            a = p.get("action") or {}
            alt = p.get("alternative") or {}
            text = f"Waiting for review: {_action_line(a)}. " + "; ".join(p.get("reasons", []))
            if alt:
                text += f". Alternative: {_action_line(alt)}."
            add(FeedRow(e.tick, "Safety rules", "Human reviewer", "NEEDS APPROVAL", text, FLAG,
                        inc_of(a), "safety"))
        elif t in (EventType.APPROVED, EventType.OVERRIDDEN):
            a = p.get("action") or {}
            who = "Human reviewer" if p.get("approver") == "human" else "Approval policy"
            verb = "Approved" if t == EventType.APPROVED else "Changed to"
            add(FeedRow(e.tick, who, "Dispatch", t.value, f"{verb}: {_action_line(a)}. "
                        f"{p.get('reason', '')}", DECISION, inc_of(a), "safety"))
        elif t == EventType.FALLBACK_USED:
            add(FeedRow(e.tick, "Rule backup", "Dispatch", "AI NOT USED",
                        f"{_fallback_text(p.get('reason', ''))} The rule-based backup decided.",
                        FLAG, p.get("incident_id") or unit_incident.get(p.get("unit_id", "")),
                        "safety", "backup"))
        elif t in (EventType.ESCALATED, EventType.APPROVED,
                   EventType.OVERRIDDEN, EventType.PRIORITY_REPORT):
            add(FeedRow(e.tick, _speaker(e.actor), str(p.get("recipient", "All")),
                        t.value.replace("_", " "), str(p.get("reason", p.get("message", ""))),
                        AGENT, p.get("incident_id"), _role(e.actor)))

    incoming: dict[str, int] = defaultdict(int)
    for pid, hid in prealerts.items():
        if patients.get(pid, {}).get("status") == "IN_TRANSPORT":
            incoming[hid] += 1
    for hid, cfg in hospital_cfg.items():
        if hid in hospitals:
            h = hospitals[hid]
            h.update(name=cfg["name"], location=cfg["location"], owner=cfg["owner"],
                     stabilization_only=cfg.get("stabilization_only", False),
                     incoming=incoming.get(hid, 0), status=hospital_status_label(h),
                     capabilities=cfg.get("capabilities", []))

    for u in units.values():  # logical place on the map (no live tracking)
        u["minutes_in_status"] = tick - u.get("since", 0)
        if u["state"] in AT_INCIDENT and u.get("incident_id") in incidents:
            u["location"] = incidents[u["incident_id"]]["location"]
        elif u["state"] in AT_HOSPITAL and u.get("hospital_id") in hospital_cfg:
            u["location"] = hospital_cfg[u["hospital_id"]]["location"]
        elif u["id"] in amb_cfg:
            u["location"] = amb_cfg[u["id"]]["home_station"]
    for row in feed:
        if row.kind == "STATUS" and "units activated" in row.text:
            for uid in units:
                if uid in row.text:
                    units[uid]["activated"] = True

    for inc in incidents.values():
        pids = [pid for pid, rec in patients.items() if rec["incident_id"] == inc["id"]]
        inc["severities"] = sorted({patients[pid]["severity"] for pid in pids})
        inc["waiting"] = sum(1 for pid in pids if patients[pid]["status"] == "WAITING_ON_SCENE")
        inc["triage"] = triage_counts(patients, pids)
        inc["units"] = sorted(u["id"] for u in units.values() if u.get("incident_id") == inc["id"])
        inc["status"] = incident_status(inc, patients, pids, units)
        inc["elapsed"] = tick - inc["call_tick"]

    called = [rec for rec in patients.values() if rec["incident_id"] in incidents]
    status_counts: dict[str, int] = defaultdict(int)
    for rec in called:
        status_counts[rec["status"]] += 1
    handling = call_handling(events)
    care = [r["care_mean_min"] for r in handling if r["care_mean_min"] is not None]
    active_units = [u for u in units.values() if u.get("activated")]
    kpis = {
        "calls": len(incidents),
        "active_calls": sum(1 for i in incidents.values() if i["status"] != "CLEARED"),
        "waiting_on_scene": status_counts["WAITING_ON_SCENE"],
        "in_transport": status_counts["IN_TRANSPORT"],
        "waiting_at_er": status_counts["WAITING_AT_ER"],
        "in_care": status_counts["IN_TREATMENT"] + status_counts["DISCHARGED"],
        "deceased": status_counts["DECEASED"],
        "free_units": sum(1 for u in active_units if u["state"] == "IDLE"),
        "units": len(active_units),
        "boarding": sum(h.get("boarding", 0) for h in hospitals.values()),
        "saturated": sum(1 for h in hospitals.values() if h.get("status") == "SATURATED"),
        "avg_call_to_care": round(sum(care) / len(care), 1) if care else None,
        "ai_decisions": decided["ai"] + decided["standin"],
        "backup_decisions": decided["backup"],
        "ai_source": ai_source if ai_calls else None,
    }
    return DashState(tick=tick, run=started, hospitals=hospitals,
                     hospital_changes=dict(changes), units=units, incidents=incidents,
                     threads=dict(threads), feed=feed, handling=handling, patients=patients,
                     kpis=kpis, ai_calls=ai_calls)


def _fallback_text(reason: str) -> str:
    """Plain-language reason an agent answer was not used."""
    r = reason.lower()
    if "max turns" in r:
        return "The AI agent ran out of steps before answering."
    if "unknown unit or call" in r:
        return "The AI named an ambulance or call that does not exist or is not free."
    if "no valid hospital" in r:
        return "The AI gave no usable hospital for this ambulance."
    if "safety-rule rejection" in r:
        return "The AI's hospital was blocked by a safety rule."
    if "unresolved" in r:
        return "Dispatch and the hospitals did not agree after 3 rounds."
    if "did not accept" in r:
        return "The hospital did not accept and negotiation is off."
    if "failed" in r:
        return "The AI agent's answer was unusable."
    return reason.capitalize() + "."


def triage_counts(patients: dict[str, dict[str, Any]], pids: list[str]) -> dict[str, dict]:
    """Triage colors by where the patients are: on scene, in transport, at hospital, died."""
    out = {c: {"total": 0, "on_scene": 0, "transport": 0, "hospital": 0, "died": 0}
           for c in TRIAGE.values()}
    for pid in pids:
        rec = patients[pid]
        c = out[rec["triage"]]
        c["total"] += 1
        status = rec["status"]
        key = {"WAITING_ON_SCENE": "on_scene", "IN_TRANSPORT": "transport",
               "DECEASED": "died"}.get(status, "hospital")
        c[key] += 1
    return out


def incident_status(inc: dict[str, Any], patients: dict[str, dict[str, Any]], pids: list[str],
                    units: dict[str, dict[str, Any]]) -> str:
    states = {u["state"] for u in units.values() if u.get("incident_id") == inc["id"]}
    statuses = {patients[pid]["status"] for pid in pids}
    if statuses <= {"IN_TREATMENT", "DISCHARGED", "DECEASED", "WAITING_AT_ER"} and \
            "WAITING_ON_SCENE" not in statuses and "IN_TRANSPORT" not in statuses:
        return "CLEARED"
    if "IN_TRANSPORT" in statuses or "TRANSPORTING" in states:
        return "TRANSPORTING"
    if states & {"ON_SCENE", "LOADING"}:
        return "ON SCENE"
    if "STAGING" in states:
        return "STAGING"
    if "EN_ROUTE" in states:
        return "UNITS EN ROUTE"
    return "PENDING"


def transport_summary(state: DashState, incident_id: str | None = None) -> dict[str, dict]:
    """Patients by hospital and triage color (EMTrack-style hospital transport summary)."""
    out: dict[str, dict[str, int]] = {}
    for rec in state.patients.values():
        if rec["incident_id"] not in state.incidents:
            continue
        if incident_id and rec["incident_id"] != incident_id:
            continue
        if not rec.get("hospital_id"):
            continue
        row = out.setdefault(rec["hospital_id"], {c: 0 for c in TRIAGE.values()})
        row[rec["triage"]] += 1
    return dict(sorted(out.items()))


# --- agent-to-agent communication -------------------------------------------------------------

NEGOTIATION = {"PROPOSE", "ACCEPT", "COUNTER", "REJECT", "ESCALATE", "RESOLVE", "STATUS"}


def speaker(actor: str) -> str:
    """Display name of a message sender or recipient, grouping all ambulances together."""
    if actor.startswith(("AMB", "PVT")):
        return "Ambulances"
    return {"agents": "Dispatch", "human": "Human reviewer", "all": "All"}.get(
        actor, _speaker(actor))


def talk_counts(events: list[Event]) -> Counter:
    """Messages sent between participants: (sender, recipient) -> count."""
    out: Counter = Counter()
    for e in events:
        if e.type == EventType.MESSAGE and e.payload["recipient"] != "all":
            out[(speaker(e.payload["sender"]), speaker(e.payload["recipient"]))] += 1
    return out


def negotiation_threads(events: list[Event]) -> list[dict[str, Any]]:
    """One thread per ambulance load: Dispatch's proposals, the hospitals' answers, any
    escalation and the allocator's ruling, and where the ambulance finally went."""
    calls = {(e.tick, e.payload["agent"]): e.payload for e in events
             if e.type == EventType.LLM_CALL}
    standin = bool(calls) and all(c["model"] == "scripted" for c in calls.values())
    threads: list[dict[str, Any]] = []
    open_: dict[str, dict[str, Any]] = {}
    for e in events:
        p = e.payload
        if e.type == EventType.MESSAGE and p["type"] in NEGOTIATION:
            units = [(p.get("proposed_action") or {}).get("unit_id")]
            if p["type"] == "RESOLVE":
                units = [r["unit_id"] for r in (p.get("proposed_action") or {}).get("routes", [])]
            for uid in filter(None, units):
                if p["type"] == "STATUS" and not p["recipient"].startswith("hospital"):
                    continue
                th = open_.get(uid)
                if th is None or (p["type"] == "PROPOSE" and p.get("negotiation_round") == 0
                                  and th["outcome"]):
                    th = {"unit": uid, "start": e.tick, "incident": p.get("incident_id"),
                          "patients": len(p.get("patient_ids") or []), "turns": [],
                          "outcome": None}
                    open_[uid] = th
                    threads.append(th)
                call = None if p.get("by_code") else calls.get((e.tick, p["sender"]))
                src = ("standin" if standin else "ai") if call else "sim"
                th["turns"].append({"tick": e.tick, "sender": speaker(p["sender"]),
                                    "recipient": speaker(p["recipient"]), "type": p["type"],
                                    "text": p.get("reason", ""), "source": src,
                                    "round": p.get("negotiation_round"), "ai": call})
        elif e.type == EventType.COMMITTED and p["action"].get("kind") == "route":
            th = open_.get(p["action"]["unit_id"])
            if th is not None and th["outcome"] is None:
                by = p["action"].get("decided_by", "")
                th["outcome"] = {"tick": e.tick, "hospital": p["action"]["hospital_id"],
                                 "by": "rule backup" if by == "rules" else "agents"}
    return threads
