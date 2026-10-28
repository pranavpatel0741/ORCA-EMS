"""Hard rules R1–R9 (PLAN §12).

Each rule returns a `CheckResult` with a level:
- `block`: the action is rejected (the only level with `ok=False`)
- `review`: allowed but needs human review (R6); approval gating arrives in M7
- `warn`: allowed, recorded as a structured warning (e.g. R2 ALL_FULL, R5 STAGING)
- `pass`

Rules read the engine's *true* state at commit time. Reasons may contain hidden truth, so they
go to the log only; policies see the rule id and code.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

import config.settings as settings
from sim.actions import (
    ACTION_TYPES,
    Action,
    ActivateMutualAid,
    Dispatch,
    LendStaff,
    RouteToHospital,
)
from sim.entities import (
    AmbulanceState,
    Capability,
    Incident,
    IncidentType,
    Owner,
    Patient,
    PatientStatus,
    Severity,
)
from sim.state_machine import can_reassign

if TYPE_CHECKING:
    from sim.engine import Engine

TRAUMA_CAPS = {Capability.TRAUMA_L1, Capability.TRAUMA_L2}
SURGE_TYPES = {IncidentType.BUS_CRASH, IncidentType.SHOOTING}
CRITICAL_THRESHOLD_MIN = 60  # PLAN §16 modeled on-time threshold

Level = Literal["pass", "block", "review", "warn"]


class CheckResult(BaseModel):
    ok: bool
    rule_id: str
    level: Level = "pass"
    code: str = ""
    reason: str = ""


Rule = Callable[[Action, "Engine"], CheckResult]


def _ok(rule: str) -> CheckResult:
    return CheckResult(ok=True, rule_id=rule)


def _block(rule: str, code: str, reason: str) -> CheckResult:
    return CheckResult(ok=False, rule_id=rule, level="block", code=code, reason=reason)


def _flag(rule: str, level: Level, code: str, reason: str) -> CheckResult:
    return CheckResult(ok=True, rule_id=rule, level=level, code=code, reason=reason)


# --- shared helpers ------------------------------------------------------------------------------


def action_patients(action: Action, engine: Engine) -> list[Patient]:
    if isinstance(action, Dispatch):
        ids = action.patient_ids
    elif isinstance(action, RouteToHospital):
        amb = engine.ambulances.get(action.unit_id)
        ids = amb.assigned_patient_ids if amb else []
    else:
        ids = []
    return [engine.patients[p] for p in ids if p in engine.patients]


def target_hospital(action: Action) -> str | None:
    if isinstance(action, Dispatch):
        return action.target_hospital
    if isinstance(action, RouteToHospital):
        return action.hospital_id
    return None


def has_capability(caps: set[Capability], needed: Capability | None) -> bool:
    if needed is None or needed == Capability.GENERAL:
        return True
    if needed in TRAUMA_CAPS:
        return bool(caps & TRAUMA_CAPS)
    return needed in caps


def capability_ok(engine: Engine, hospital_id: str, p: Patient) -> bool:
    """Capability check; a stabilization-only bay may take critical trauma (R3 decides when)."""
    hs = engine.hospitals[hospital_id]
    if has_capability(hs.config.capabilities, p.needs.capability):
        return True
    stab = hs.config.stabilization_only and hs.config.trauma_bays_total > 0
    return stab and is_critical_trauma(p)


def is_critical_trauma(p: Patient) -> bool:
    return p.true_severity == Severity.CRITICAL and p.needs.trauma_bay


def surge_active(engine: Engine) -> bool:
    return any(i.type in SURGE_TYPES for i in engine.active_incidents.values())


def contract_allows(engine: Engine, hospital_id: str, patients: list[Patient]) -> tuple[bool, str]:
    """R4 hospital side. Private hospitals take ambulance patients only under their surge
    contract, and only while a surge (bus crash / shooting) is active."""
    hs = engine.hospitals[hospital_id]
    if hs.config.owner != Owner.PRIVATE:
        return True, ""
    contract = hs.config.surge_contract
    if contract is None:
        return False, "NO_CONTRACT"
    if not surge_active(engine):
        return False, "NO_SURGE"
    for p in patients:
        if p.true_severity not in contract.eligible_severities:
            return False, "SEVERITY_NOT_ELIGIBLE"
        if (p.needs.trauma_bay or p.needs.trauma_surgeon) and not contract.accepts_critical_trauma:
            return False, "TRAUMA_NOT_ACCEPTED"
    already = engine.contract_patient_count(hospital_id, exclude={p.id for p in patients})
    if already + len(patients) > contract.max_surge_patients:
        return False, "CONTRACT_LIMIT"
    return True, ""


def fully_capable(engine: Engine, hospital_id: str, patients: list[Patient]) -> bool:
    """Can definitively treat these patients: capability, every resource type, not a
    stabilization-only bay for trauma, and allowed by contract."""
    hs = engine.hospitals[hospital_id]
    for p in patients:
        if not has_capability(hs.config.capabilities, p.needs.capability):
            return False
        if p.needs.trauma_bay and hs.config.stabilization_only:
            return False
        if not hs.has_resource_types(engine.demand_at(hospital_id, p)):
            return False
    return contract_allows(engine, hospital_id, patients)[0]


def hospital_can_take(engine: Engine, hospital_id: str, patients: list[Patient], eta: int) -> bool:
    hs = engine.hospitals[hospital_id]
    incoming = engine.incoming_demands(hospital_id, exclude={p.id for p in patients})
    for p in patients:
        demand = engine.demand_at(hospital_id, p)
        if not hs.has_resource_types(demand) or not hs.can_accept(demand, eta, incoming):
            return False
        incoming = [*incoming, demand]
    return True


# --- R1: unit exists, assignable, not committed elsewhere ----------------------------------------


def r1_unit_assignable(action: Action, engine: Engine) -> CheckResult:
    if isinstance(action, LendStaff | ActivateMutualAid):
        return _ok("R1")
    amb = engine.ambulances.get(action.unit_id)
    if amb is None:
        return _block("R1", "UNKNOWN_UNIT", f"unknown unit {action.unit_id}")
    if action.unit_id in engine.committed_units_this_tick:
        return _block("R1", "ALREADY_COMMITTED", f"{amb.id} already committed this tick")
    if action.unit_id in engine.awaiting_approval_units() and not engine.approving:
        return _block("R1", "PENDING_APPROVAL", f"{amb.id} has a decision awaiting approval")
    if isinstance(action, Dispatch):
        if len(set(action.patient_ids)) != len(action.patient_ids):
            return _block("R1", "DUPLICATE_PATIENT", "duplicate patient ids")
        if not can_reassign(amb):
            return _block("R1", "NOT_ASSIGNABLE", f"{amb.id} not assignable in {amb.state}")
        if not engine.unit_available(amb.id):
            return _block("R1", "NOT_ACTIVATED", f"{amb.id} is not activated")
        inc = engine.active_incidents.get(action.incident_id)
        if inc is None:
            return _block("R1", "INCIDENT_NOT_ACTIVE", f"incident {action.incident_id}")
        for pid in action.patient_ids:
            p = engine.patients.get(pid)
            if p is None or p.incident_id != inc.id:
                return _block("R1", "PATIENT_NOT_AT_INCIDENT", f"{pid} not at {inc.id}")
            if p.status != PatientStatus.WAITING_ON_SCENE:
                return _block("R1", "PATIENT_NOT_WAITING", f"{pid} is {p.status}")
            if p.ambulance_id not in (None, amb.id):
                return _block("R1", "PATIENT_TAKEN", f"{pid} assigned to {p.ambulance_id}")
        return _ok("R1")
    if amb.state not in (AmbulanceState.ON_SCENE, AmbulanceState.LOADING):
        return _block("R1", "NOT_ROUTABLE", f"{amb.id} cannot be routed in {amb.state}")
    if not amb.assigned_patient_ids:
        return _block("R1", "NO_PATIENTS", f"{amb.id} has no patients to transport")
    return _ok("R1")


# --- R2: destination resources at expected arrival -----------------------------------------------


def r2_hospital_resources(action: Action, engine: Engine) -> CheckResult:
    hid = target_hospital(action)
    if hid is None:
        return _ok("R2")
    if hid not in engine.hospitals:
        return _block("R2", "UNKNOWN_HOSPITAL", hid)
    patients = action_patients(action, engine)
    if not patients:
        return _block("R2", "TARGET_WITHOUT_PATIENTS",
                      "a target hospital requires the patients to be named")
    if not all(capability_ok(engine, hid, p) for p in patients):
        return _block("R2", "MISSING_CAPABILITY", f"{hid} lacks a required capability")
    if hospital_can_take(engine, hid, patients, engine.expected_arrival(action, hid)):
        return _ok("R2")
    # All-full clause: if no fully capable hospital is projected to have capacity at its ETA,
    # any fully capable hospital passes and the patient will queue (structured warning).
    capable = [h for h in sorted(engine.hospitals) if fully_capable(engine, h, patients)]
    if hid in capable and not any(
        hospital_can_take(engine, h, patients, engine.expected_arrival(action, h))
        for h in capable
    ):
        return _flag("R2", "warn", "ALL_FULL", "no capable hospital has capacity; will queue")
    return _block("R2", "NO_CAPACITY_AT_ETA", f"{hid} lacks resources at ETA")


# --- R3: critical trauma destinations ------------------------------------------------------------


def _most_unstable(engine: Engine, p: Patient) -> bool:
    peers = [engine.patients[q] for q in engine.incidents[p.incident_id].true_victim_ids]
    peers = [q for q in peers if q.true_severity == Severity.CRITICAL
             and q.status == PatientStatus.WAITING_ON_SCENE]
    def key(q: Patient) -> tuple[float, str]:
        return (q.survival_prob if q.survival_prob is not None else 1.0, q.id)
    return min(peers, key=key).id == p.id if peers else True


def _trauma_center_in_time(engine: Engine, action: Action, p: Patient) -> bool:
    threshold = p.needs.or_within_minutes or CRITICAL_THRESHOLD_MIN
    for hid in sorted(engine.hospitals):
        if not fully_capable(engine, hid, [p]):
            continue
        hs = engine.hospitals[hid]
        eta = engine.expected_arrival(action, hid)
        start = hs.earliest_fit(engine.demand_at(hid, p), eta,
                                engine.incoming_demands(hid, exclude={p.id}))
        if start is not None and start - p.timestamps.call <= threshold:
            return True
    return False


def r3_critical_trauma(action: Action, engine: Engine) -> CheckResult:
    hid = target_hospital(action)
    if hid is None or hid not in engine.hospitals:
        return _ok("R3")
    hs = engine.hospitals[hid]
    for p in action_patients(action, engine):
        if not is_critical_trauma(p):
            continue
        caps = hs.config.capabilities
        if hs.config.stabilization_only:
            if not _most_unstable(engine, p):
                return _block("R3", "STABILIZATION_NOT_MOST_UNSTABLE",
                              f"{p.id} is not the most unstable critical patient")
            if _trauma_center_in_time(engine, action, p):
                return _block("R3", "TRAUMA_CENTER_REACHABLE",
                              "a trauma center can start definitive care in time")
            continue
        if not (caps & TRAUMA_CAPS) or hs.config.trauma_surgeons_total == 0 \
                or hs.config.trauma_bays_total == 0:
            return _block("R3", "NOT_TRAUMA_CENTER", f"{hid} cannot treat critical trauma")
        if p.needs.or_within_minutes is not None:
            deadline = engine.expected_arrival(action, hid) + p.needs.or_within_minutes
            if hs.config.ors_total == 0 or not hs.or_available_by(deadline):
                return _flag("R3", "review", "OR_LATE",
                             f"no OR free at {hid} within {p.needs.or_within_minutes} min")
    return _ok("R3")


# --- R4: private contracts -----------------------------------------------------------------------


def r4_private_contracts(action: Action, engine: Engine) -> CheckResult:
    if isinstance(action, ActivateMutualAid):
        firm = engine.firms.get(action.firm_id)
        if firm is None:
            return _block("R4", "UNKNOWN_FIRM", action.firm_id)
        if action.units < 1:
            return _block("R4", "BAD_UNIT_COUNT", "units must be >= 1")
        used = engine.mutual_aid_units(firm.id)
        if used + action.units > firm.max_mutual_aid_units:
            return _block("R4", "MUTUAL_AID_LIMIT",
                          f"{used} + {action.units} > {firm.max_mutual_aid_units}")
        if used + action.units > len(firm.unit_ids):
            return _block("R4", "NOT_ENOUGH_UNITS", f"{firm.id} has {len(firm.unit_ids)} units")
        return _ok("R4")
    hid = target_hospital(action)
    if hid is None or hid not in engine.hospitals:
        return _ok("R4")
    ok, code = contract_allows(engine, hid, action_patients(action, engine))
    return _ok("R4") if ok else _block("R4", code, f"{hid} contract does not allow this")


# --- R5: no entry to unsecured violent scenes ----------------------------------------------------


def scene_entry_allowed(inc: Incident) -> bool:
    """Engine-side R5 check before any unit goes ON_SCENE."""
    return not inc.violent or inc.scene_secured


def r5_scene_safety(action: Action, engine: Engine) -> CheckResult:
    if not isinstance(action, Dispatch):
        return _ok("R5")
    inc = engine.incidents.get(action.incident_id)
    if inc is not None and not scene_entry_allowed(inc):
        return _flag("R5", "warn", "STAGING", "scene unsecured; unit will stage")
    return _ok("R5")


# --- R6: mandatory human review ------------------------------------------------------------------


def r6_human_review(action: Action, engine: Engine) -> CheckResult:
    hid = target_hospital(action)
    if hid is None or hid not in engine.hospitals:
        return _ok("R6")
    critical = [p for p in action_patients(action, engine) if p.true_severity == Severity.CRITICAL]
    if not critical:
        return _ok("R6")
    codes, reasons = [], []
    eta = engine.expected_arrival(action, hid)
    if not hospital_can_take(engine, hid, critical, eta):
        codes.append("R6a")
        reasons.append(f"critical patient would wait for resources at {hid}")
    capable = [h for h in sorted(engine.hospitals) if fully_capable(engine, h, critical)]
    if capable:
        nearest = min(engine.expected_arrival(action, h) for h in capable)
        if eta - nearest > settings.R6_DETOUR_MIN:
            codes.append("R6b")
            reasons.append(f"routed {eta - nearest} min past the nearest capable hospital")
    if codes:
        return _flag("R6", "review", "+".join(codes), "; ".join(reasons))
    return _ok("R6")


# --- R7: ambulance capacity ----------------------------------------------------------------------


def r7_ambulance_capacity(action: Action, engine: Engine) -> CheckResult:
    if not isinstance(action, Dispatch):
        return _ok("R7")
    patients = action_patients(action, engine)
    n_crit = sum(1 for p in patients if p.true_severity == Severity.CRITICAL)
    if n_crit and len(patients) > 1:
        return _block("R7", "CRITICAL_NOT_ALONE", "a critical patient must travel alone")
    if len(patients) > 2:
        return _block("R7", "OVER_CAPACITY", "at most 2 non-critical patients per ambulance")
    return _ok("R7")


# --- R8: staff loans -----------------------------------------------------------------------------


def r8_staff_loans(action: Action, engine: Engine) -> CheckResult:
    if not isinstance(action, LendStaff):
        return _ok("R8")
    if action.lender_id == action.borrower_id:
        return _block("R8", "SELF_LOAN", "lender and borrower must differ")
    if action.lender_id not in engine.hospitals or action.borrower_id not in engine.hospitals:
        return _block("R8", "UNKNOWN_HOSPITAL", "unknown lender or borrower")
    if action.nurses < 1:
        return _block("R8", "BAD_NURSE_COUNT", "nurses must be >= 1")
    if not engine.hospitals[action.lender_id].can_lend(action.nurses):
        return _block("R8", "BELOW_COVERAGE", "loan would breach minimum nurse coverage")
    return _ok("R8")


# --- R9: only known actions; agents cannot modify capacity ---------------------------------------


def r9_known_action(action: Action, engine: Engine) -> CheckResult:
    if not isinstance(action, ACTION_TYPES):
        return _block("R9", "UNKNOWN_ACTION", f"{type(action).__name__} is not an allowed action")
    return _ok("R9")


class Validator:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules: list[Rule] = rules if rules is not None else default_rules()

    def check(self, action: Action, engine: Engine) -> list[CheckResult]:
        r9 = r9_known_action(action, engine)
        if not r9.ok:
            return [r9]
        return [rule(action, engine) for rule in self.rules]


def default_rules() -> list[Rule]:
    return [
        r1_unit_assignable,
        r2_hospital_resources,
        r3_critical_trauma,
        r4_private_contracts,
        r5_scene_safety,
        r6_human_review,
        r7_ambulance_capacity,
        r8_staff_loans,
        r9_known_action,
    ]
