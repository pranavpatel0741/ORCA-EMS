"""Agent orchestration (PLAN §14.3–14.7). Plain Python, not an LLM.

Each tick, only when a decision is needed:
1. New call or new scene report -> Assessment agent -> PRIORITY_REPORT to Dispatch.
2. Dispatch agent -> DispatchPlan (unit assignments, hospital choices, mutual aid).
3. Each hospital choice -> PROPOSE to that Hospital agent -> ACCEPT / REJECT / COUNTER.
   A hospital short of nurses may ask another hospital (STAFF_REQUEST / STAFF_RESPONSE).
4. COUNTER / REJECT -> Dispatch revises with the feedback, up to 3 rounds.
5. Still unresolved, or two plans want the same ambulance -> Allocator -> RESOLVE.
6. Confidence gate for critical patients -> execute, information round, or escalate (human
   review through the engine's approval path) -> actions returned to the engine, which
   validates and commits them.

`agents_no_negotiation` uses the same agents, but a hospital COUNTER / REJECT falls back to the
rule-based choice, and the Allocator is never called.

Fallbacks: if an agent fails (timeout, malformed output after one retry, invalid IDs), the
rule-based baseline decides that piece and FALLBACK_USED is logged. A cache miss in cache_only
mode is not a fallback: it fails loudly.
"""

from __future__ import annotations

import os
from typing import Any

import config.settings as settings
from baselines.nearest import can_treat
from baselines.rule_based import RuleBasedPolicy
from orca_agents import allocator, assessment, dispatch, hospital_agent
from orca_agents.confidence import score
from orca_agents.llm_cache import AgentSpec, CacheMiss, LLMClient, OpenAIAgentsBackend
from orca_agents.models import AdmissionDecision, DispatchPlan, PriorityReport, Resolution
from orca_agents.tools import AgentContext, patient_brief
from sim.actions import Action, ActivateMutualAid, Dispatch, LendStaff, RouteToHospital
from sim.entities import Severity
from sim.observations import Observation

STAFF_COOLDOWN_MIN = 30


class AgentFailure(RuntimeError):
    pass


def default_client() -> LLMClient:
    mode = settings.LLM_MODE
    backend = None
    if mode != "cache_only" and os.getenv("OPENAI_API_KEY") and settings.OPENAI_MODEL:
        backend = OpenAIAgentsBackend()
    return LLMClient(backend=backend, mode=mode)


RULES_TAG = "[rule backup]"  # marks rationales of actions the rule-based backup chose


class AgentPolicy:
    def __init__(self, negotiate: bool = True, client: LLMClient | None = None) -> None:
        self.negotiate = negotiate
        self.name = "agents" if negotiate else "agents_no_negotiation"
        self.client = client or default_client()
        self.fallback = RuleBasedPolicy()
        self.reports: dict[str, PriorityReport] = {}
        self._assessed: dict[str, bool] = {}  # incident -> scene_reported at last assessment
        self.feedback: dict[str, list[dict[str, Any]]] = {}  # unit -> counters / rejections
        self._staff_asked: dict[str, int] = {}  # borrower -> last request tick
        self._negotiated: set[str] = set()  # units whose destination was already negotiated
        self._rule_rejected: dict[str, set[str]] = {}  # unit -> hospitals the rules rejected
        self._last_signature: tuple | None = None

    # --- plumbing ------------------------------------------------------------------------------

    def _call(self, obs: Observation, spec: AgentSpec, payload: dict[str, Any],
              hospital_id: str | None = None, extra: dict | None = None):
        ctx = AgentContext(obs=obs, hospital_id=hospital_id, extra=extra or {})
        last_error: Exception | None = None
        for attempt in range(2):  # one retry on malformed output / transient errors
            try:
                out, record = self.client.call(spec, payload if attempt == 0 else
                                               {**payload, "retry": attempt}, ctx)
                obs.llm_calls.append(record.as_event())
                return out
            except CacheMiss:
                raise
            except Exception as exc:  # noqa: BLE001 - any agent failure triggers the fallback
                last_error = exc
        raise AgentFailure(f"{spec.agent_id}: {last_error}")

    def _fallback(self, obs: Observation, reason: str, **payload: Any) -> None:
        obs.events.append({"type": "FALLBACK_USED", "actor": self.name,
                           "payload": {"reason": reason, **payload}})

    # --- 1. assessment -------------------------------------------------------------------------

    def _assess(self, obs: Observation) -> None:
        for inc in sorted(obs.incidents.values(), key=lambda i: (i.call_tick, i.id)):
            if self._assessed.get(inc.id) == inc.scene_reported:
                continue
            try:
                report = self._call(obs, assessment.SPEC, assessment.payload(inc))
            except AgentFailure as exc:
                self._fallback(obs, f"assessment failed: {exc}", incident_id=inc.id)
                self._assessed[inc.id] = inc.scene_reported
                continue
            self.reports[inc.id] = report
            self._assessed[inc.id] = inc.scene_reported
            e = report.estimated
            obs.send("assessment", "dispatch", "PRIORITY_REPORT",
                     f"{report.mode}: about {e.critical} critical, {e.serious} serious, "
                     f"{e.minor} minor; urgency {report.urgency:.1f}. {report.rationale}",
                     incident_id=inc.id, proposed_action=report.model_dump(mode="json"))
            obs.events.append({"type": "PRIORITY_REPORT", "actor": "assessment",
                               "payload": {"incident_id": inc.id, "recipient": "dispatch",
                                           **report.model_dump(mode="json"),
                                           "reason": report.rationale}})

    # --- 2. dispatch ---------------------------------------------------------------------------

    def _signature(self, obs: Observation) -> tuple:
        """What the Dispatch agent would see; unchanged means no new decision is needed."""
        return (tuple(sorted(u.id for u in obs.free_units())),
                tuple(sorted(p.id for i in obs.incidents for p in obs.waiting(i))),
                tuple(sorted((i, obs.unassigned_victims(i)) for i, inc in obs.incidents.items()
                             if not inc.patients)),
                tuple(sorted(u.id for u in obs.units_needing_destination())),
                tuple(sorted((u, h) for u, hs in self._rule_rejected.items() for h in hs)))

    def _needs_dispatch(self, obs: Observation) -> bool:
        work = any(obs.waiting(i) or (not inc.patients and obs.unassigned_victims(i))
                   for i, inc in obs.incidents.items())
        critical_waiting = any(p.severity == Severity.CRITICAL for i in obs.incidents
                               for p in obs.waiting(i))
        return bool((work and obs.free_units()) or obs.units_needing_destination()
                    or (critical_waiting and not obs.free_units()))

    def _plan(self, obs: Observation, focus: set[str] | None = None) -> DispatchPlan:
        fb = [f for unit, items in self.feedback.items() for f in items
              if focus is None or unit in focus]
        return self._call(obs, dispatch.SPEC,
                          dispatch.payload(obs, self.reports, fb, focus, self._declined()))

    def _declined(self) -> dict[str, set[str]]:
        """Hospitals that already said no (counter, reject, or safety rule) to each ambulance."""
        return {u: {f["hospital_id"] for f in items} for u, items in self.feedback.items()}

    def _assignments(self, obs: Observation, plan: DispatchPlan
                     ) -> tuple[list[Action], list[dict[str, Any]]]:
        actions: list[Action] = []
        conflicts: list[dict[str, Any]] = []
        free = {u.id for u in obs.free_units()}
        used: set[str] = set()
        invented = sorted({a.unit_id for a in plan.assignments if a.unit_id not in obs.units})
        if invented:  # one note per plan, not one per made-up unit
            self._fallback(obs, "dispatch named ambulances that do not exist: "
                           + ", ".join(invented), unit_id="")
        for a in plan.assignments:
            if a.unit_id in invented:
                continue
            if not a.incident_id.strip():
                continue  # the model listed a unit with no call: nothing to do
            unit = obs.units.get(a.unit_id)
            if unit is not None and a.unit_id not in free and (
                    unit.patient_ids or unit.state not in ("EN_ROUTE", "STAGING")):
                continue  # restates a unit that is already busy with its patients: no-op
            inc = obs.incidents.get(a.incident_id)
            if inc is None and (p := obs.patient(a.incident_id)):
                inc = obs.incidents.get(p.incident_id)  # a patient ID given as the call
            if inc is None or unit is None:
                self._fallback(obs, "dispatch named an unknown unit or call", unit_id=a.unit_id,
                               incident_id=a.incident_id)
                continue
            if a.unit_id not in free and unit.assigned_incident == inc.id:
                continue  # already heading there; the crew takes the most severe on scene
            waiting = {p.id for p in obs.waiting(inc.id)}
            pids = [p for p in a.patient_ids if p in waiting]
            if a.patient_ids and not pids:
                continue
            if a.unit_id in used:
                conflicts.append({"type": "duplicate", "unit_id": a.unit_id,
                                  "to_call": inc.id, "patient_ids": pids})
                continue
            if a.unit_id in free:
                used.add(a.unit_id)
                actions.append(Dispatch(unit_id=a.unit_id, incident_id=inc.id,
                                        patient_ids=pids, rationale=a.rationale))
                obs.send("dispatch", a.unit_id, "STATUS", a.rationale, incident_id=inc.id,
                         patient_ids=pids)
            elif unit.state in ("EN_ROUTE", "STAGING") and unit.reassignable:
                frm = unit.assigned_incident
                conflicts.append({
                    "type": "reassign", "unit_id": a.unit_id, "from_call": frm,
                    "to_call": inc.id, "patient_ids": pids,
                    "from_has_critical": self._call_has_critical(obs, frm),
                    "to_has_critical": any(obs.patient(p) and obs.patient(p).severity ==
                                           Severity.CRITICAL for p in pids)})
                used.add(a.unit_id)
        return actions, conflicts

    def _call_has_critical(self, obs: Observation, incident_id: str | None) -> bool:
        """Known critical patients waiting, or (before a scene report) the Assessment agent's
        estimate of critical victims."""
        inc = obs.incidents.get(incident_id or "")
        if inc is None:
            return False
        if inc.patients:
            return any(p.severity == Severity.CRITICAL and p.status == "WAITING_ON_SCENE"
                       for p in inc.patients)
        report = self.reports.get(inc.id)
        return bool(report and report.estimated.critical > 0) or inc.violent

    # --- 3-5. negotiation ----------------------------------------------------------------------

    def _ask_hospitals(self, obs: Observation, proposals: dict[str, str], round_: int,
                       offers: list[dict[str, Any]], actions: list[Action]) -> dict[str, str]:
        """PROPOSE each unit's patients to its hospital; return units that were accepted."""
        settled: dict[str, str] = {}
        by_hospital: dict[str, list[str]] = {}
        for unit, hid in sorted(proposals.items()):
            by_hospital.setdefault(hid, []).append(unit)
        for hid, units in sorted(by_hospital.items()):
            props = []
            for uid in units:
                u = obs.units[uid]
                pats = [patient_brief(p) for pid in u.patient_ids if (p := obs.patient(pid))]
                eta = obs.eta(u.location, obs.hospitals[hid].location)
                props.append({"unit_id": uid, "eta_min": eta, "patients": pats})
                obs.send("dispatch", f"hospital:{hid}", "PROPOSE",
                         f"{uid} with {len(pats)} patient(s), ETA {eta:.0f} min. Can you take "
                         "them?", patient_ids=u.patient_ids, negotiation_round=round_,
                         incident_id=u.assigned_incident,
                         proposed_action={"unit_id": uid, "hospital_id": hid})
            try:
                decision: AdmissionDecision = self._call(
                    obs, hospital_agent.spec(obs, hid),
                    hospital_agent.admission_payload(obs, hid, props), hospital_id=hid)
            except AgentFailure as exc:
                self._fallback(obs, f"hospital agent failed: {exc}", hospital_id=hid)
                continue
            accepted = set(decision.accepted_patient_ids) if decision.decision != "ACCEPT" \
                else {p["id"] for pr in props for p in pr["patients"]}
            for pr in props:
                uid = pr["unit_id"]
                ok = all(p["id"] in accepted for p in pr["patients"])
                mtype = "ACCEPT" if ok else decision.decision
                text = decision.rationale if ok else \
                    f"{decision.counter_offer or decision.rationale}".strip()
                obs.send(f"hospital:{hid}", "dispatch", mtype, text,
                         incident_id=obs.units[uid].assigned_incident,
                         patient_ids=[p["id"] for p in pr["patients"]],
                         negotiation_round=round_,
                         proposed_action={"unit_id": uid, "hospital_id": hid,
                                          "suggested_hospital": decision.suggested_hospital})
                offers.append({"unit_id": uid, "hospital_id": hid, "decision": mtype,
                               "counter": decision.counter_offer,
                               "suggested_hospital": decision.suggested_hospital})
                if ok:
                    settled[uid] = hid
                else:
                    self.feedback.setdefault(uid, []).append({
                        "unit_id": uid, "hospital_id": hid, "type": mtype,
                        "counter": decision.counter_offer,
                        "suggested_hospital": decision.suggested_hospital})
            if decision.staff_request_nurses > 0:
                self._staff(obs, hid, decision.staff_request_nurses, actions)
        return settled

    def _staff(self, obs: Observation, borrower: str, nurses: int, actions: list[Action]) -> None:
        if obs.tick - self._staff_asked.get(borrower, -999) < STAFF_COOLDOWN_MIN:
            return
        self._staff_asked[borrower] = obs.tick
        lenders = sorted((h for h in obs.hospitals if h != borrower
                          and obs.hospitals[h].owner == "PUBLIC"),
                         key=lambda h: (-(obs.own_status[h]["nurses_on_duty"]
                                          - obs.own_status[h]["min_nurse_coverage"]), h))
        if not lenders:
            return
        lender = lenders[0]
        why = f"Hospital {borrower} needs {nurses} nurse(s) to accept incoming patients"
        obs.send(f"hospital:{borrower}", f"hospital:{lender}", "STAFF_REQUEST", why,
                 proposed_action={"nurses": nurses})
        try:
            answer = self._call(obs, hospital_agent.spec(obs, lender, staff=True),
                                hospital_agent.staff_payload(obs, lender, borrower, nurses, why),
                                hospital_id=lender)
        except AgentFailure as exc:
            self._fallback(obs, f"staff decision failed: {exc}", hospital_id=lender)
            return
        obs.send(f"hospital:{lender}", f"hospital:{borrower}", "STAFF_RESPONSE",
                 answer.rationale, proposed_action={"nurses": answer.lend_nurses})
        if answer.lend_nurses > 0:
            actions.append(LendStaff(lender_id=lender, borrower_id=borrower,
                                     nurses=answer.lend_nurses, rationale=answer.rationale))

    def _resolve(self, obs: Observation, conflicts: list[dict[str, Any]],
                 offers: list[dict[str, Any]]) -> Resolution | None:
        for c in conflicts:
            obs.send("dispatch", "allocator", "ESCALATE",
                     f"{c['type'].replace('_', ' ')}: {c.get('unit_id')}",
                     incident_id=c.get("to_call"), proposed_action=c, by_code=True)
        try:
            res: Resolution = self._call(obs, allocator.SPEC,
                                         allocator.payload(obs, conflicts, offers,
                                                           self._declined()),
                                         extra={"conflicts": conflicts, "offers": offers})
        except AgentFailure as exc:
            self._fallback(obs, f"allocator failed: {exc}")
            return None
        obs.send("allocator", "dispatch", "RESOLVE", res.rationale,
                 proposed_action=res.model_dump(mode="json"),
                 negotiation_round=settings.MAX_NEGOTIATION_ROUNDS + 1)
        return res

    # --- 6. confidence gate --------------------------------------------------------------------

    def _route_action(self, obs: Observation, uid: str, hid: str, rationale: str,
                      force_review: bool = False) -> RouteToHospital:
        unit = obs.units[uid]
        patients = [p for pid in unit.patient_ids if (p := obs.patient(pid))]
        if not any(p.severity == Severity.CRITICAL for p in patients):
            return RouteToHospital(unit_id=uid, hospital_id=hid, rationale=rationale,
                                   needs_review=force_review)
        clean = not any(r.action.get("unit_id") == uid for r in obs.rejections)
        conf = score(obs, uid, hid, patients, validator_clean=clean)
        verdict = conf.decision()
        if verdict == "info_round":  # ask the hospital for its live status, then recompute
            live = obs.own_status[hid]["free"]
            obs.send("dispatch", f"hospital:{hid}", "STATUS",
                     f"Confidence {conf.score:.2f}; requesting your current status.",
                     patient_ids=unit.patient_ids, by_code=True,
                     proposed_action={"unit_id": uid, "hospital_id": hid})
            conf = score(obs, uid, hid, patients, validator_clean=clean, live_free=live)
            verdict = "execute" if conf.decision() == "execute" else "escalate"
        review = force_review or verdict == "escalate"
        if review:
            obs.send("dispatch", "human", "ESCALATE",
                     f"Confidence {conf.score:.2f} for {uid} → Hospital {hid}; asking for "
                     "review.", patient_ids=unit.patient_ids,
                     incident_id=unit.assigned_incident, by_code=True,
                     proposed_action={"unit_id": uid, "hospital_id": hid})
        return RouteToHospital(unit_id=uid, hospital_id=hid, rationale=rationale,
                               confidence=conf.score, needs_review=review)

    # --- decide --------------------------------------------------------------------------------

    def decide(self, obs: Observation) -> list[Action]:
        """Agent decisions, each tagged with who made it: an LLM agent or the rule backup.

        At most one order per ambulance per minute: a route beats a dispatch, and a later
        order (e.g. the allocator's ruling) replaces an earlier one of the same kind."""
        per_unit: dict[str, Action] = {}
        other: list[Action] = []
        for a in self._decide(obs):
            uid = getattr(a, "unit_id", None)
            if uid is None:
                other.append(a)
            elif not (a.kind == "dispatch" and getattr(per_unit.get(uid), "kind", "") ==
                      "route"):
                per_unit[uid] = a
        return [a.model_copy(update={"decided_by": "rules" if a.rationale.startswith(
            ("rule-based", RULES_TAG)) else "ai"}) for a in [*per_unit.values(), *other]]

    def _decide(self, obs: Observation) -> list[Action]:
        self.fallback._note_rejections(obs)
        for r in obs.rejections:
            if r.action.get("kind") == "route":
                uid = r.action["unit_id"]
                self._rule_rejected.setdefault(uid, set()).add(r.action["hospital_id"])
                self.feedback.setdefault(uid, []).append({
                    "unit_id": uid, "hospital_id": r.action["hospital_id"], "type": "RULE",
                    "counter": f"safety rule {r.rule_id} ({r.code})", "suggested_hospital": None})
        needing = {u.id for u in obs.units_needing_destination()}
        self.feedback = {u: f for u, f in self.feedback.items() if u in needing}
        self._rule_rejected = {u: h for u, h in self._rule_rejected.items() if u in needing}
        self._negotiated &= needing

        self._assess(obs)
        signature = self._signature(obs)
        if not self._needs_dispatch(obs) or signature == self._last_signature:
            return []
        self._last_signature = signature
        try:
            plan = self._plan(obs)
        except AgentFailure as exc:
            self._fallback(obs, f"dispatch failed: {exc}")
            return [a.model_copy(update={"rationale": f"{RULES_TAG} {a.rationale}".strip()})
                    for a in self.fallback.decide(obs)]

        actions, conflicts = self._assignments(obs, plan)
        if plan.mutual_aid and (firm := obs.firms.get(plan.mutual_aid.firm_id)):
            left = min(firm.max_units, len(firm.unit_ids)) - firm.in_use
            if left > 0:  # ask for no more units than the firm still has
                actions.append(ActivateMutualAid(firm_id=firm.id,
                                                 units=min(plan.mutual_aid.units, left),
                                                 rationale=plan.rationale))

        def allowed(uid: str, hid: str) -> bool:
            return hid in obs.hospitals and hid not in self._rule_rejected.get(uid, set())

        def fresh_offer(uid: str, hid: str) -> bool:
            """Dispatch may not re-propose a hospital that already said no to this ambulance;
            that goes to the Allocator instead of repeating the same question."""
            return allowed(uid, hid) and hid not in self._declined().get(uid, set())

        # A unit whose agreed destination was later rejected by the safety rules is not
        # renegotiated every minute: the rule-based choice (which skips rejected hospitals)
        # takes over.
        for uid in sorted(needing & self._negotiated):
            hid = self.fallback.choose_hospital(obs, obs.units[uid])
            if hid:
                self._fallback(obs, "re-route after a safety-rule rejection", unit_id=uid)
                actions.append(RouteToHospital(unit_id=uid, hospital_id=hid,
                                               rationale="rule-based re-route"))
        fresh = needing - self._negotiated
        proposals = {r.unit_id: r.hospital_id for r in plan.routes
                     if r.unit_id in fresh and allowed(r.unit_id, r.hospital_id)}
        rationale = {r.unit_id: r.rationale for r in plan.routes}
        for uid in sorted(fresh - set(proposals)):
            hid = self.fallback.choose_hospital(obs, obs.units[uid])
            if hid:
                self._fallback(obs, "dispatch proposed no valid hospital", unit_id=uid)
                actions.append(RouteToHospital(unit_id=uid, hospital_id=hid,
                                               rationale="rule-based fallback"))
        self._negotiated |= set(proposals)

        offers: list[dict[str, Any]] = []
        settled: dict[str, str] = {}
        round_ = 0
        while proposals:
            accepted = self._ask_hospitals(obs, proposals, round_, offers, actions)
            settled.update(accepted)
            remaining = {u: h for u, h in proposals.items() if u not in accepted}
            if not remaining:
                break
            if not self.negotiate:
                for uid in sorted(remaining):
                    hid = self.fallback.choose_hospital(obs, obs.units[uid])
                    if hid:
                        self._fallback(obs, "hospital did not accept; no negotiation",
                                       unit_id=uid)
                        actions.append(RouteToHospital(unit_id=uid, hospital_id=hid,
                                                       rationale="rule-based fallback"))
                proposals = {}
                break
            round_ += 1
            if round_ > settings.MAX_NEGOTIATION_ROUNDS:
                conflicts += [{"type": "route_unresolved", "unit_id": u, "last_hospital": h}
                              for u, h in sorted(remaining.items())]
                proposals = {}
                break
            try:
                revised = self._plan(obs, focus=set(remaining))
            except AgentFailure as exc:
                self._fallback(obs, f"dispatch revision failed: {exc}")
                revised = DispatchPlan(rationale="")
            proposals = {r.unit_id: r.hospital_id for r in revised.routes
                         if r.unit_id in remaining and fresh_offer(r.unit_id, r.hospital_id)}
            rationale.update({r.unit_id: r.rationale for r in revised.routes})
            for uid in sorted(set(remaining) - set(proposals)):
                conflicts.append({"type": "route_unresolved", "unit_id": uid,
                                  "last_hospital": remaining[uid]})

        escalate_units: set[str] = set()
        if conflicts and self.negotiate:
            res = self._resolve(obs, conflicts, offers)
            if res:
                for r in res.routes:
                    if r.unit_id in needing and allowed(r.unit_id, r.hospital_id) \
                            and r.unit_id not in settled:
                        settled[r.unit_id] = r.hospital_id
                        rationale[r.unit_id] = r.rationale
                        if res.escalate:
                            escalate_units.add(r.unit_id)
                for a in res.assignments:
                    u = obs.units.get(a.unit_id)
                    if u and u.reassignable and a.incident_id in obs.incidents:
                        actions.append(Dispatch(unit_id=a.unit_id, incident_id=a.incident_id,
                                                patient_ids=a.patient_ids,
                                                rationale=a.rationale))
        for c in conflicts:  # anything still unsettled falls back to the rule-based choice
            uid = c.get("unit_id")
            if c["type"] == "route_unresolved" and uid not in settled and uid in needing:
                hid = self.fallback.choose_hospital(obs, obs.units[uid])
                if hid:
                    self._fallback(obs, "negotiation unresolved", unit_id=uid)
                    settled[uid] = hid
                    rationale[uid] = "rule-based fallback after negotiation"

        for uid, hid in sorted(settled.items()):
            if not can_treat(obs.hospitals[hid], [p for pid in obs.units[uid].patient_ids
                                                   if (p := obs.patient(pid))],
                             obs.surge_active):
                pass  # the safety rules will judge; keep the agents' choice visible
            actions.append(self._route_action(obs, uid, hid, rationale.get(uid, ""),
                                              force_review=uid in escalate_units))
        return actions
