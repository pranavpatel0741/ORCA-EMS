"""Deterministic stand-in for the LLM (tests and offline integration checks only).

It reads the same JSON input a real agent gets and returns the same typed output, following the
agents' instructions with simple rules. It never calls the network. Results from this backend
are never reported as LLM results.
"""

from __future__ import annotations

import json
import math
from typing import Any

from pydantic import BaseModel

from orca_agents.llm_cache import AgentSpec
from orca_agents.models import (
    AdmissionDecision,
    Assignment,
    DispatchPlan,
    MutualAid,
    PriorityReport,
    Resolution,
    RouteChoice,
    SeverityCounts,
    StaffDecision,
)

ORDER = {"CRITICAL": 0, "SERIOUS": 1, "MINOR": 2, "EXPECTANT": 3, None: 1}
MCI = {"BUS_CRASH", "SHOOTING"}
TRAUMA = {"TRAUMA_L1", "TRAUMA_L2"}


def _demand(p: dict[str, Any], stabilization: bool = False) -> dict[str, int]:
    needs = p.get("needs") or {}
    if needs.get("trauma_bay"):
        d = {"trauma_bay": 1, "nurse_slot": 2}
        if not stabilization:
            d["surgeon"] = 1
        return d
    return {"er_bed": 1, "nurse_slot": 2 if p.get("severity") == "CRITICAL" else 1}


def _capable(h: dict[str, Any], p: dict[str, Any], surge: bool) -> bool:
    needs = p.get("needs") or {}
    cap = needs.get("capability")
    caps = set(h.get("capabilities", []))
    if needs.get("trauma_bay") and (h.get("stabilization_only") or not caps & TRAUMA):
        return False
    if cap and cap != "GENERAL" and cap not in caps and not (cap in TRAUMA and caps & TRAUMA):
        return False
    if h.get("owner") == "PRIVATE":
        c = h.get("contract") or {}
        if not surge or p.get("severity") not in c.get("eligible_severities", []) \
                or needs.get("trauma_bay"):
            return False
    return True


def _fits(free: dict[str, int], patients: list[dict], stabilization: bool = False) -> bool:
    need: dict[str, int] = {}
    for p in patients:
        for r, n in _demand(p, stabilization).items():
            need[r] = need.get(r, 0) + n
    return all(free.get(r, 0) >= n for r, n in need.items())


class ScriptedBackend:
    model = "scripted"

    def run(self, spec: AgentSpec, payload: dict[str, Any], context: Any) -> tuple[BaseModel, int]:
        kind = spec.agent_id.split(":")[0]
        if kind == "hospital":
            out = (self.staff if spec.output_type is StaffDecision else self.admission)(payload)
        else:
            out = getattr(self, kind)(payload)
        return out, len(json.dumps(payload)) // 4

    # --- assessment ----------------------------------------------------------------------------

    def assessment(self, pl: dict[str, Any]) -> PriorityReport:
        call, rep = pl["call"], pl["scene_report"]
        mci = call["type"] in MCI or call["reported_victims"] > 4
        if rep:
            counts = SeverityCounts(**{k: v for k, v in rep.items() if k in SeverityCounts
                                       .model_fields})
        elif mci:
            n = call["reported_victims"]
            crit = max(1, round(0.18 * n)) if call["type"] != "SHOOTING" else n
            ser = round(0.32 * n) if call["type"] != "SHOOTING" else 0
            counts = SeverityCounts(critical=crit, serious=ser, minor=max(0, n - crit - ser))
        else:
            sev = "critical" if call["type"] in ("MEDICAL_CARDIAC", "MEDICAL_STROKE") else \
                "serious" if call["type"] == "VEHICLE_CRASH" else "minor"
            counts = SeverityCounts(**{sev: call["reported_victims"]})
        urgency = 1.0 if mci else 0.9 if counts.critical else 0.6 if counts.serious else 0.3
        return PriorityReport(incident_id=call["id"], mode="MCI" if mci else "SINGLE",
                              estimated=counts, needs_police=call["violent"],
                              needs_fire=call["trapped_victims"], urgency=urgency,
                              rationale=f"{'Mass-casualty' if mci else 'Single'} call; "
                                        f"{counts.critical} critical expected.")

    # --- dispatch ------------------------------------------------------------------------------

    def dispatch(self, pl: dict[str, Any]) -> DispatchPlan:
        surge = pl["surge_active"]
        calls = sorted(pl["calls"], key=lambda c: (
            min([ORDER[p["severity"]] for p in c["waiting_patients"]] or [1]),
            -(c["urgency"] or 0), c["called_min"], c["id"]))
        free = {u["id"]: u for u in pl["free_units"]}
        assignments, uncovered_critical = [], []
        for c in calls:
            pats = sorted(c["waiting_patients"], key=lambda p: (ORDER[p["severity"]], p["id"]))
            groups = [[p] for p in pats if p["severity"] == "CRITICAL"]
            rest = [p for p in pats if p["severity"] != "CRITICAL"]
            groups += [rest[i:i + 2] for i in range(0, len(rest), 2)]
            groups += [[] for _ in range(math.ceil(c["victims_not_yet_seen"] / 2))]
            for g in groups:
                if not free:
                    if g and g[0]["severity"] == "CRITICAL":
                        uncovered_critical.append((c["id"], g[0]["id"]))
                    continue
                uid = min(free, key=lambda u: (free[u]["eta_to_calls_min"][c["id"]], u))
                del free[uid]
                assignments.append(Assignment(unit_id=uid, incident_id=c["id"],
                                              patient_ids=[p["id"] for p in g],
                                              rationale="nearest free unit for the most "
                                                        "severe waiting patients"))
        critical_calls = {cid for cid, _ in uncovered_critical}
        for u in pl["en_route_units"]:  # propose moving a unit to an uncovered critical patient
            if uncovered_critical and u["going_to"] not in critical_calls:
                cid, pid = uncovered_critical.pop(0)
                assignments.append(Assignment(unit_id=u["id"], incident_id=cid,
                                              patient_ids=[pid],
                                              rationale="reassign: a critical patient has no "
                                                        "unit"))
        aid = None
        firms = [f for f in pl["private_firms"] if f["units_left"] > 0]
        if uncovered_critical and firms:
            aid = MutualAid(firm_id=firms[0]["id"],
                            units=min(firms[0]["units_left"], len(uncovered_critical)))
        routes = [self._route(u, pl, surge) for u in pl["loaded_units"]]
        return DispatchPlan(assignments=assignments, routes=[r for r in routes if r],
                            mutual_aid=aid, rationale="severity first, nearest capable "
                                                      "hospital with space on the board")

    def _route(self, unit: dict[str, Any], pl: dict[str, Any], surge: bool) -> RouteChoice | None:
        hospitals = {h["id"]: h for h in pl["hospitals"]}
        tried = {f["hospital_id"]: f for f in pl["feedback"] if f.get("unit_id") == unit["id"]}
        suggested = [f["suggested_hospital"] for f in tried.values()
                     if f.get("suggested_hospital") and f["suggested_hospital"] not in tried]
        pats = unit["patients"]
        capable = [h for h in sorted(hospitals, key=lambda h: (unit["eta_to_hospitals_min"][h], h))
                   if all(_capable(hospitals[h], p, surge) for p in pats)]
        if suggested and suggested[0] in capable:
            return RouteChoice(unit_id=unit["id"], hospital_id=suggested[0],
                               rationale=f"Hospital {tried and list(tried)[-1]} suggested it")
        fresh = [h for h in capable if h not in tried] or capable
        with_space = [h for h in fresh if _fits(hospitals[h]["free"], pats)]
        choice = (with_space or fresh or [None])[0]
        if choice is None:
            return None
        return RouteChoice(unit_id=unit["id"], hospital_id=choice,
                           rationale="nearest capable hospital with space on the board"
                           if with_space else "nearest capable hospital; all look full")

    # --- hospitals -----------------------------------------------------------------------------

    def admission(self, pl: dict[str, Any]) -> AdmissionDecision:
        st = pl["my_status"]
        free = dict(st["free"])
        for p in pl["already_incoming"]:
            for r, n in _demand(p, st["stabilization_only"]).items():
                free[r] = free.get(r, 0) - n
        accepted, refused, capability_gap, nurse_short = [], [], False, 0
        host = {"capabilities": st["capabilities"], "stabilization_only": st["stabilization_only"],
                "owner": "PRIVATE" if st["contract"] else "PUBLIC", "contract": st["contract"]}
        for prop in pl["proposals"]:
            for p in prop["patients"]:
                if not _capable(host, p, st["surge_active"]):
                    capability_gap = True
                    refused.append(p["id"])
                    continue
                d = _demand(p, st["stabilization_only"])
                if all(free.get(r, 0) >= n for r, n in d.items()):
                    accepted.append(p["id"])
                    for r, n in d.items():
                        free[r] -= n
                else:
                    refused.append(p["id"])
                    if all(free.get(r, 0) >= n for r, n in d.items() if r != "nurse_slot"):
                        nurse_short += 1
        hid = pl["hospital"]
        if not refused:
            return AdmissionDecision(hospital_id=hid, decision="ACCEPT",
                                     accepted_patient_ids=accepted,
                                     rationale="Beds and staff are available at arrival.")
        if capability_gap and not accepted:
            return AdmissionDecision(hospital_id=hid, decision="REJECT",
                                     rationale="We cannot treat this kind of patient.")
        return AdmissionDecision(
            hospital_id=hid, decision="COUNTER", accepted_patient_ids=accepted,
            counter_offer=f"can take {len(accepted)} of {len(accepted) + len(refused)} now",
            staff_request_nurses=1 if nurse_short else 0,
            rationale="Not enough free beds or staff for everyone proposed.")

    def staff(self, pl: dict[str, Any]) -> StaffDecision:
        st, req = pl["my_status"], pl["request"]
        spare = st["nurses_on_duty"] - st["min_nurse_coverage"]
        spare_slots = st["free"].get("nurse_slot", 0) // 4
        lend = max(0, min(req["nurses"], spare, spare_slots))
        return StaffDecision(hospital_id=pl["hospital"], lend_nurses=lend,
                             rationale=f"We can spare {lend} nurse(s) and stay above minimum "
                                       "coverage." if lend else "We need every nurse we have.")

    # --- allocator -----------------------------------------------------------------------------

    def allocator(self, pl: dict[str, Any]) -> Resolution:
        hospitals = {h["id"]: h for h in pl["hospitals"]}
        units = {u["id"]: u for u in pl["units"]}
        routes, assignments, escalate = [], [], False
        for c in pl["conflicts"]:
            if c["type"] == "reassign":
                if c["to_has_critical"] and not c["from_has_critical"]:
                    assignments.append(Assignment(unit_id=c["unit_id"], incident_id=c["to_call"],
                                                  patient_ids=c["patient_ids"],
                                                  rationale="critical patient outranks the "
                                                            "unit's current call"))
                continue
            u = units.get(c["unit_id"])
            if not u:
                continue
            rejected = {o["hospital_id"] for o in pl["offers"]
                        if o["unit_id"] == u["id"] and o["decision"] in ("REJECT", "RULE")}
            capable = [h for h in hospitals if h not in rejected
                       and all(_capable(hospitals[h], p, True) for p in u["patients"])]
            roomy = sorted(capable, key=lambda h: (
                -hospitals[h]["free"].get("er_bed", 0), u["eta_to_hospitals_min"][h], h))
            spaced = [h for h in roomy if _fits(hospitals[h]["free"], u["patients"])]
            choice = (spaced or sorted(capable, key=lambda h: u["eta_to_hospitals_min"][h])
                      or [None])[0]
            if choice:
                routes.append(RouteChoice(unit_id=u["id"], hospital_id=choice,
                                          rationale="most room among capable hospitals"
                                          if spaced else "no hospital has room; nearest"))
            if not spaced and any(p["severity"] == "CRITICAL" for p in u["patients"]):
                escalate = True
        return Resolution(routes=routes, assignments=assignments, escalate=escalate,
                          rationale="Spread patients to hospitals with room; critical first.")
