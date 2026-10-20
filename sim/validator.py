"""Hard rules (PLAN §12). Each check returns a `CheckResult`; any failure blocks the commit.

M2 implements R1, R2, R7. R3–R6, R8, R9 are added in M3.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from pydantic import BaseModel

from sim.actions import Action, Dispatch, LendStaff, RouteToHospital
from sim.entities import AmbulanceState, Capability, Patient, PatientStatus, Severity
from sim.hospital import resource_demand
from sim.state_machine import can_reassign

if TYPE_CHECKING:
    from sim.engine import Engine

TRAUMA_CAPS = {Capability.TRAUMA_L1, Capability.TRAUMA_L2}


class CheckResult(BaseModel):
    ok: bool
    rule_id: str
    reason: str = ""


Rule = Callable[[Action, "Engine"], CheckResult]


def _ok(rule: str) -> CheckResult:
    return CheckResult(ok=True, rule_id=rule)


def _fail(rule: str, reason: str) -> CheckResult:
    return CheckResult(ok=False, rule_id=rule, reason=reason)


def action_patients(action: Action, engine: Engine) -> list[Patient]:
    if isinstance(action, Dispatch):
        ids = action.patient_ids
    elif isinstance(action, RouteToHospital):
        amb = engine.ambulances.get(action.unit_id)
        ids = amb.assigned_patient_ids if amb else []
    else:
        ids = []
    return [engine.patients[p] for p in ids if p in engine.patients]


def has_capability(caps: set[Capability], needed: Capability | None) -> bool:
    if needed is None or needed == Capability.GENERAL:
        return True
    if needed in TRAUMA_CAPS:
        return bool(caps & TRAUMA_CAPS)
    return needed in caps


# --- R1: unit exists, assignable, not committed elsewhere ----------------------------------------


def r1_unit_assignable(action: Action, engine: Engine) -> CheckResult:
    if isinstance(action, LendStaff):
        return _ok("R1")
    amb = engine.ambulances.get(action.unit_id)
    if amb is None:
        return _fail("R1", f"unknown unit {action.unit_id}")
    if action.unit_id in engine.committed_units_this_tick:
        return _fail("R1", f"{amb.id} already committed this tick")
    if isinstance(action, Dispatch):
        if not can_reassign(amb):
            return _fail("R1", f"{amb.id} not assignable in state {amb.state}")
        if not engine.unit_available(amb.id):
            return _fail("R1", f"{amb.id} is not activated")
        inc = engine.active_incidents.get(action.incident_id)
        if inc is None:
            return _fail("R1", f"incident {action.incident_id} not active")
        for pid in action.patient_ids:
            p = engine.patients.get(pid)
            if p is None or p.incident_id != inc.id:
                return _fail("R1", f"patient {pid} not at incident {inc.id}")
            if p.status != PatientStatus.WAITING_ON_SCENE:
                return _fail("R1", f"patient {pid} is {p.status}")
            if p.ambulance_id not in (None, amb.id):
                return _fail("R1", f"patient {pid} already assigned to {p.ambulance_id}")
        return _ok("R1")
    # RouteToHospital
    if amb.state not in (AmbulanceState.ON_SCENE, AmbulanceState.LOADING):
        return _fail("R1", f"{amb.id} cannot be routed in state {amb.state}")
    if not amb.assigned_patient_ids:
        return _fail("R1", f"{amb.id} has no patients to transport")
    return _ok("R1")


# --- R2: destination resources at expected arrival -----------------------------------------------


def _target(action: Action) -> str | None:
    if isinstance(action, Dispatch):
        return action.target_hospital
    if isinstance(action, RouteToHospital):
        return action.hospital_id
    return None


def hospital_can_take(engine: Engine, hospital_id: str, patients: list[Patient], eta: int) -> bool:
    hs = engine.hospitals[hospital_id]
    exclude = {p.id for p in patients}
    incoming = engine.incoming_demands(hospital_id, exclude=exclude)
    for p in patients:
        demand = resource_demand(p.needs, p.true_severity)
        if not has_capability(hs.config.capabilities, p.needs.capability):
            return False
        if not hs.has_resource_types(demand):
            return False
        if not hs.can_accept(demand, eta, incoming):
            return False
        incoming = [*incoming, demand]
    return True


def r2_hospital_resources(action: Action, engine: Engine) -> CheckResult:
    hid = _target(action)
    if hid is None:
        return _ok("R2")
    if hid not in engine.hospitals:
        return _fail("R2", f"unknown hospital {hid}")
    patients = action_patients(action, engine)
    if not patients:
        return _ok("R2")
    if hospital_can_take(engine, hid, patients, engine.eta_tick_for(action, hid)):
        return _ok("R2")
    # All-full clause: if no hospital that structurally can treat these patients has projected
    # capacity at its ETA, any structurally capable hospital passes (the patient will queue).
    capable = [h for h in engine.hospitals if engine.structurally_capable(h, patients)]
    if hid in capable and not any(
        hospital_can_take(engine, h, patients, engine.eta_tick_for(action, h))
        for h in capable
    ):
        return CheckResult(ok=True, rule_id="R2", reason="all-full clause: patient will queue")
    return _fail("R2", f"hospital {hid} lacks resources for {[p.id for p in patients]} at ETA")


# --- R7: ambulance capacity ----------------------------------------------------------------------


def r7_ambulance_capacity(action: Action, engine: Engine) -> CheckResult:
    if not isinstance(action, Dispatch):
        return _ok("R7")
    patients = action_patients(action, engine)
    n_crit = sum(1 for p in patients if p.true_severity == Severity.CRITICAL)
    if n_crit and len(patients) > 1:
        return _fail("R7", "a critical patient must travel alone")
    if len(patients) > 2:
        return _fail("R7", "at most 2 non-critical patients per ambulance")
    return _ok("R7")


class Validator:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules: list[Rule] = rules if rules is not None else default_rules()

    def check(self, action: Action, engine: Engine) -> list[CheckResult]:
        return [rule(action, engine) for rule in self.rules]


def default_rules() -> list[Rule]:
    return [r1_unit_assignable, r2_hospital_resources, r7_ambulance_capacity]
