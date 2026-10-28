"""Deterministic tick loop and commit API (PLAN §3, §15 M2).

The engine is the only source of truth. Policies propose `Action`s; the engine validates and
commits them. Tick order (one tick = one simulated minute):

  1. advance clock
  2. complete unit transitions and move units
  3. finish treatments, release resources, admit from ER queues
  4. patient deterioration and outcome updates
  5. new incidents, walk-ins, scene events, staff loans, mutual aid, background arrivals
  6. collect decisions from the active policy (R9 fingerprint around the call)
  7. validate and commit
  8. log hospital status changes; run invariant hook

A patient admitted at tick t is never also marked dead at t (step 3 runs before step 4).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from typing import Any, Protocol

import config.settings as settings
from protocol.messages import Message, MessageType
from sim.actions import (
    Action,
    ActivateMutualAid,
    Dispatch,
    LendStaff,
    RouteToHospital,
)
from sim.entities import (
    Ambulance,
    AmbulanceState,
    Incident,
    Location,
    Owner,
    Patient,
    PatientStatus,
    ResponderTeam,
    Scenario,
    Severity,
    TeamKind,
    TeamState,
)
from sim.events import EventLog, EventType
from sim.hospital import (
    PATIENTS_PER_NURSE,
    RESOURCES,
    SEVERITY_PRIORITY,
    HospitalState,
    QueueItem,
    resource_demand,
)
from sim.observations import (
    Observation,
    ObsFirm,
    ObsHospital,
    ObsIncident,
    ObsPatient,
    ObsUnit,
    Rejection,
)
from sim.outcomes import is_dead, survival_probability
from sim.state_machine import (
    can_reassign,
    secure_scene,
    transition_ambulance,
    transition_patient,
    transition_team,
)
from sim.travel import (
    Sampler,
    TimingConfig,
    estimate_eta,
    interpolate,
    midpoint,
    offset_point,
)
from sim.validator import Validator, scene_entry_allowed, surge_active

A = AmbulanceState
MOVING = {A.EN_ROUTE, A.TRANSPORTING, A.RETURNING}
ACTIVE_PATIENT = {PatientStatus.WAITING_ON_SCENE, PatientStatus.IN_TRANSPORT,
                  PatientStatus.WAITING_AT_ER}
INITIAL_UNIT_STATES = {A.IDLE, A.RETURNING}


class Policy(Protocol):
    name: str

    def decide(self, obs: Observation) -> list[Action]: ...


class R9Violation(RuntimeError):
    """A policy changed engine state outside `commit` (PLAN R9)."""


class Leg:
    """A straight-line movement between two points over [start, end] ticks."""

    __slots__ = ("origin", "dest", "start", "end", "target")

    def __init__(self, origin: Location, dest: Location, start: int, end: int, target: str):
        self.origin, self.dest, self.start, self.end, self.target = origin, dest, start, end, target

    def position(self, tick: int) -> Location:
        span = max(1, self.end - self.start)
        return interpolate(self.origin, self.dest, (tick - self.start) / span)


class StaffLoan:
    __slots__ = ("lender", "borrower", "nurses", "arrive_tick", "return_tick", "phase")

    def __init__(self, lender: str, borrower: str, nurses: int, arrive_tick: int, return_tick: int):
        self.lender, self.borrower, self.nurses = lender, borrower, nurses
        self.arrive_tick, self.return_tick = arrive_tick, return_tick
        self.phase = "DEPARTED"  # DEPARTED -> ARRIVED -> RETURNING -> (removed)


class Engine:
    def __init__(
        self,
        scenario: Scenario,
        policy: Policy | None = None,
        *,
        timing: TimingConfig | None = None,
        validator: Validator | None = None,
        run_id: str | None = None,
        tick_hook: Callable[[Engine], None] | None = None,
        info: str | None = None,
    ) -> None:
        self.scenario = scenario
        self.policy = policy
        self.info = info or scenario.info
        self.timing = timing or TimingConfig()
        self.validator = validator or Validator()
        self.sampler = Sampler(scenario.seed, self.timing)
        self.run_id = run_id or f"s{scenario.seed:02d}_{scenario.demand}_{self.info}_" + (
            policy.name if policy else "none"
        )
        self.log = EventLog(self.run_id)
        self.tick_hook = tick_hook

        sc = scenario.model_copy(deep=True)
        self.hospitals: dict[str, HospitalState] = {
            h.id: HospitalState(config=h) for h in sc.hospitals
        }
        self.ambulances: dict[str, Ambulance] = {a.id: a for a in sc.ambulances}
        self.teams: dict[str, ResponderTeam] = {t.id: t for t in sc.teams}
        self.firms = {f.id: f for f in sc.firms}
        self.incidents: dict[str, Incident] = {i.id: i for i in sc.incidents}
        self.patients: dict[str, Patient] = {p.id: p for p in sc.patients}
        self.walk_ins = sc.walk_ins
        self.patient_u = {pid: self.sampler.patient_uniforms(i)
                          for i, pid in enumerate(sorted(self.patients))}
        self._firm_of = {uid: f.id for f in sc.firms for uid in f.unit_ids}

        self.tick = 0
        self.state_version = 0
        self.active_incidents: dict[str, Incident] = {}
        self.closed_incidents: set[str] = set()
        self.legs: dict[str, Leg] = {}
        self.activated_units: set[str] = {
            a.id for a in sc.ambulances if a.owner == Owner.PUBLIC
        }
        self.pending_mutual_aid: list[tuple[str, int, int]] = []  # (firm, units, ready_tick)
        self.pending_team_requests: list[tuple[str, TeamKind]] = []
        self.extrication_done: dict[str, int] = {}
        self.loans: list[StaffLoan] = []
        self.committed_units_this_tick: set[str] = set()
        self.commits: list[dict[str, Any]] = []
        # unit -> (patients, hospital) of the last validated destination decision
        self.validated_dest: dict[str, tuple[frozenset[str], str]] = {}
        self._last_status: dict[str, dict] = {}
        self._bg_rate: dict[str, float] = {}
        self._ward_rate: dict[str, float] = {}
        self._initialized = False
        self._summarized = False
        self._message_seq = 0
        self.decision_timings: list[dict[str, Any]] = []
        self.board: dict[str, dict[str, Any]] = {}  # hospital status board (PLAN §11)
        self.board_tick = -1
        self._rejections: list[Rejection] = []  # fed back to the policy as rule codes only

    # ==========================================================================================
    # Queries used by the validator, policies, and observations
    # ==========================================================================================

    def unit_available(self, unit_id: str) -> bool:
        return unit_id in self.activated_units

    def position(self, unit_id: str) -> Location:
        leg = self.legs.get(unit_id)
        if leg is not None:
            return leg.position(self.tick)
        if unit_id in self.ambulances:
            return self.ambulances[unit_id].location
        return self.teams[unit_id].location

    def demand_at(self, hospital_id: str, p: Patient) -> dict[str, int]:
        stab = self.hospitals[hospital_id].config.stabilization_only and p.needs.trauma_bay
        return resource_demand(p.needs, p.true_severity, stabilization_only=stab)

    def incoming_patients(self, hospital_id: str, exclude: set[str] | None = None) -> list[Patient]:
        """Patients committed to `hospital_id` but not yet arrived."""
        exclude = exclude or set()
        out = []
        for amb in self.ambulances.values():
            if amb.destination_hospital != hospital_id:
                continue
            for pid in amb.assigned_patient_ids:
                p = self.patients[pid]
                if pid not in exclude and p.status in (PatientStatus.WAITING_ON_SCENE,
                                                       PatientStatus.IN_TRANSPORT):
                    out.append(p)
        return out

    def incoming_demands(self, hospital_id: str, exclude: set[str] | None = None) -> list[dict]:
        return [self.demand_at(hospital_id, p) for p in self.incoming_patients(hospital_id,
                                                                                exclude)]

    def contract_patient_count(self, hospital_id: str, exclude: set[str] | None = None) -> int:
        """Ambulance patients admitted to or committed to `hospital_id` (R4 contract limit)."""
        exclude = exclude or set()
        arrived = sum(1 for p in self.patients.values()
                      if p.hospital_id == hospital_id and not p.walk_in and p.id not in exclude)
        return arrived + len(self.incoming_patients(hospital_id, exclude))

    def mutual_aid_units(self, firm_id: str) -> int:
        active = sum(1 for uid in self.activated_units if self._firm_of.get(uid) == firm_id)
        pending = sum(n for f, n, _ in self.pending_mutual_aid if f == firm_id)
        return active + pending

    def expected_arrival(self, action: Action, hospital_id: str) -> int:
        """Expected arrival tick at `hospital_id` for the unit in `action`.

        Uses the median travel estimate and the midpoint of the severity-specific scene and
        loading ranges. This is the single ETA model shared by the validator, baselines, and
        agents (PLAN §9)."""
        cfg = self.timing
        hloc = self.hospitals[hospital_id].config.location
        if isinstance(action, Dispatch):
            inc = self.incidents[action.incident_id]
            pats = [self.patients[p] for p in action.patient_ids if p in self.patients]
            critical = any(p.true_severity == Severity.CRITICAL for p in pats)
            scene = midpoint(cfg.scene_time_critical if critical else cfg.scene_time_other)
            to_scene = estimate_eta(self.position(action.unit_id), inc.location, cfg)
            to_hosp = estimate_eta(inc.location, hloc, cfg)
            return self.tick + round(to_scene["median_min"] + scene + midpoint(cfg.loading)
                                     + to_hosp["median_min"])
        amb = self.ambulances[action.unit_id]
        remaining = 0.0
        if amb.state == A.LOADING:
            if amb.state_until_tick is not None:
                remaining = max(0, amb.state_until_tick - self.tick)
        elif amb.state == A.ON_SCENE:
            left = (amb.state_until_tick - self.tick if amb.state_until_tick is not None
                    else midpoint(cfg.scene_time_other))
            remaining = max(0, left) + midpoint(cfg.loading)
        to_hosp = estimate_eta(self.position(amb.id), hloc, cfg)
        return self.tick + round(remaining + to_hosp["median_min"])

    def waiting_patients(self, incident_id: str) -> list[Patient]:
        inc = self.incidents[incident_id]
        return [
            self.patients[p] for p in inc.true_victim_ids
            if self.patients[p].status == PatientStatus.WAITING_ON_SCENE
        ]

    def units_needing_destination(self) -> list[Ambulance]:
        return [
            a for a in self.ambulances.values()
            if a.state in (A.ON_SCENE, A.LOADING) and a.assigned_patient_ids
            and a.destination_hospital is None
        ]

    # ==========================================================================================
    # Commit API
    # ==========================================================================================

    def commit(self, action: Action, actor: str = "policy") -> bool:
        results = self.validator.check(action, self)
        blocks = [r for r in results if r.level == "block"]
        flags = [{"rule_id": r.rule_id, "level": r.level, "code": r.code, "reason": r.reason}
                 for r in results if r.level in ("review", "warn")]
        dumped = action.model_dump(mode="json") if hasattr(action, "model_dump") else {
            "kind": type(action).__name__}
        record = {"tick": self.tick, "actor": actor, "action": dumped,
                  "results": [r.model_dump() for r in results], "committed": not blocks}
        self.commits.append(record)
        if blocks:
            for f in blocks:
                self.log.emit(self.tick, EventType.PROPOSAL_REJECTED, actor,
                              {"action": dumped, "rule_id": f.rule_id, "code": f.code,
                               "reason": f.reason})
                self._rejections.append(Rejection(tick=self.tick, action=dumped,
                                                  rule_id=f.rule_id, code=f.code))
            return False
        self.log.emit(self.tick, EventType.PROPOSAL_VALIDATED, actor,
                      {"action": dumped, "flags": flags})
        self._apply(action, actor)
        self.state_version += 1
        self.log.emit(self.tick, EventType.COMMITTED, actor,
                      {"action": dumped, "state_version": self.state_version})
        return True

    def _apply(self, action: Action, actor: str) -> None:
        if isinstance(action, Dispatch):
            self._apply_dispatch(action, actor)
        elif isinstance(action, RouteToHospital):
            self._apply_route(action, actor)
        elif isinstance(action, LendStaff):
            self._apply_loan(action, actor)
        elif isinstance(action, ActivateMutualAid):
            self._apply_mutual_aid(action, actor)

    def _apply_dispatch(self, action: Dispatch, actor: str) -> None:
        amb = self.ambulances[action.unit_id]
        self.committed_units_this_tick.add(amb.id)
        for pid in amb.assigned_patient_ids:  # reassignment releases previous patients
            if self.patients[pid].ambulance_id == amb.id:
                self.patients[pid].ambulance_id = None
        inc = self.incidents[action.incident_id]
        amb.assigned_incident = inc.id
        amb.assigned_patient_ids = list(action.patient_ids)
        amb.destination_hospital = action.target_hospital
        self.validated_dest.pop(amb.id, None)
        if action.target_hospital is not None:
            self.validated_dest[amb.id] = (frozenset(action.patient_ids), action.target_hospital)
        for pid in action.patient_ids:
            self.patients[pid].ambulance_id = amb.id
        self._start_leg_to_incident(amb, inc, actor)

    def _start_leg_to_incident(self, amb: Ambulance, inc: Incident, actor: str) -> None:
        origin = self.position(amb.id)
        if not scene_entry_allowed(inc):
            dest = offset_point(inc.location, origin, self.timing.staging_offset_km)
            target = "staging"
        else:
            dest, target = inc.location, "scene"
        minutes = self.sampler.travel(origin, dest)
        amb.location = origin
        self.legs[amb.id] = Leg(origin, dest, self.tick, self.tick + minutes, target)
        transition_ambulance(amb, A.EN_ROUTE, self.tick, self.log, until=self.tick + minutes,
                             actor=actor, incident_id=inc.id, target=target,
                             patient_ids=list(amb.assigned_patient_ids))

    def _apply_route(self, action: RouteToHospital, actor: str) -> None:
        amb = self.ambulances[action.unit_id]
        self.committed_units_this_tick.add(amb.id)
        amb.destination_hospital = action.hospital_id
        self.validated_dest[amb.id] = (frozenset(amb.assigned_patient_ids), action.hospital_id)
        if amb.state == A.LOADING and amb.state_until_tick is None:
            self._start_transport(amb)

    def _apply_loan(self, action: LendStaff, actor: str) -> None:
        lender = self.hospitals[action.lender_id]
        lender.nurses_loaned_out += action.nurses
        arrive = self.tick + self.sampler.minutes(self.timing.staff_transfer, stream="staff")
        loan = StaffLoan(action.lender_id, action.borrower_id, action.nurses, arrive,
                         arrive + self.timing.staff_loan_duration)
        self.loans.append(loan)
        self.log.emit(self.tick, EventType.STAFF_LOAN, actor,
                      {"lender": loan.lender, "borrower": loan.borrower, "nurses": loan.nurses,
                       "arrive_tick": loan.arrive_tick, "return_tick": loan.return_tick,
                       "phase": "DEPARTED"})

    def _apply_mutual_aid(self, action: ActivateMutualAid, actor: str) -> None:
        firm = self.firms[action.firm_id]
        ready = self.tick + firm.activation_minutes
        self.pending_mutual_aid.append((firm.id, action.units, ready))
        self.send(actor, f"firm:{firm.id}", MessageType.MUTUAL_AID_REQUEST,
                  f"request {action.units} mutual-aid unit(s)",
                  proposed_action={"units": action.units})
        self.send(f"firm:{firm.id}", actor, MessageType.MUTUAL_AID_RESPONSE,
                  f"accepted; {action.units} unit(s) ready at tick {ready}",
                  proposed_action={"units": action.units, "ready_tick": ready})

    def send(self, sender: str, recipient: str, type: MessageType, reason: str, *,
             incident_id: str | None = None, patient_ids: list[str] | None = None,
             proposed_action: dict[str, Any] | None = None, negotiation_round: int = 0) -> Message:
        """Log a protocol message (PLAN §14.1) as a MESSAGE event."""
        self._message_seq += 1
        msg = Message(message_id=f"M-{self._message_seq:05d}", tick=self.tick,
                      state_version=self.state_version, sender=sender, recipient=recipient,
                      type=type, incident_id=incident_id, patient_ids=list(patient_ids or []),
                      proposed_action=proposed_action, reason=reason,
                      negotiation_round=negotiation_round)
        self.log.emit(self.tick, EventType.MESSAGE, sender, msg.model_dump(mode="json"))
        return msg

    # ==========================================================================================
    # Tick loop
    # ==========================================================================================

    @property
    def end_tick(self) -> int:
        return self.scenario.horizon + self.scenario.drain_min

    def initialize(self) -> None:
        """Set up initial hospital load, log RUN_STARTED, and process tick 0 (steps 5–8)."""
        bg = self.sampler.stream("background")
        lo, hi = self.timing.er_background
        for hid in sorted(self.scenario.initial_occupancy):
            hs = self.hospitals[hid]
            n = round(self.scenario.initial_occupancy[hid] * hs.config.er_beds_total)
            for _ in range(n):
                # Steady-state residual stay: length-biased total stay, uniform elapsed share.
                while True:
                    stay = self.sampler.minutes((lo, hi), float(bg.random()))
                    if bg.random() < stay / hi:
                        break
                remaining = max(1, int(bg.integers(1, stay + 1)))
                hs.add_background_patient(0, stay, in_treatment=True, remaining=remaining)
            self._bg_rate[hid] = n / midpoint((lo, hi)) if self.scenario.background_arrivals else 0
        wlo, whi = self.timing.ward_stay
        for hid in sorted(self.scenario.initial_ward_occupancy):
            hs = self.hospitals[hid]
            n = round(self.scenario.initial_ward_occupancy[hid] * hs.total("ward_bed"))
            for _ in range(n):
                stay = self.sampler.minutes((wlo, whi), float(bg.random()))
                remaining = max(1, int(bg.integers(1, stay + 1)))
                hs.add_background_ward_patient(0, stay, remaining=remaining, force=True)
            self._ward_rate[hid] = n / midpoint((wlo, whi)) \
                if self.scenario.background_arrivals else 0
        for amb in sorted(self.ambulances.values(), key=lambda a: a.id):
            if amb.state not in INITIAL_UNIT_STATES:
                raise ValueError(f"{amb.id}: initial state must be IDLE or RETURNING")
            if amb.state == A.RETURNING:
                until = amb.state_until_tick or 1
                amb.state_until_tick = until
                self.legs[amb.id] = Leg(amb.location, amb.home_station, 0, until, "home")
        self.log.emit(0, EventType.RUN_STARTED, "engine", self._run_started_payload())
        self._initialized = True
        self._events_and_decisions()

    def _run_started_payload(self) -> dict[str, Any]:
        sc = self.scenario
        return {
            "seed": sc.seed, "demand": sc.demand, "info": sc.info, "horizon": sc.horizon,
            "population": sc.population, "town": sc.town,
            "end_tick": self.end_tick,
            "policy": self.policy.name if self.policy else None,
            "timing": self.timing.model_dump(mode="json"),
            "hospitals": [h.model_dump(mode="json") for h in sc.hospitals],
            "ambulances": [{"id": a.id, "owner": a.owner, "unit_type": a.unit_type,
                            "home_station": a.home_station} for a in sc.ambulances],
            "incidents": [{"id": i.id, "type": i.type, "call_tick": i.call_tick,
                           "location": i.location, "violent": i.violent,
                           "victims": len(i.true_victim_ids)} for i in sc.incidents],
            "patients": [{"id": p.id, "incident_id": p.incident_id, "severity": p.true_severity,
                          "needs": p.needs.model_dump(mode="json"), "call_tick": p.timestamps.call}
                         for p in sorted(sc.patients, key=lambda p: p.id)],
        }

    def step(self) -> None:
        if not self._initialized:
            self.initialize()
            return
        self.tick += 1  # 1
        self.committed_units_this_tick = set()
        self._advance_units()  # 2
        self._advance_teams()
        self._hospital_flow()  # 3
        self._deterioration()  # 4
        self._events_and_decisions()  # 5–8

    def run(self, until: int | None = None) -> EventLog:
        until = self.end_tick if until is None else min(until, self.end_tick)
        if not self._initialized:
            self.initialize()
        while self.tick < until:
            self.step()
        if self.tick >= self.end_tick:
            self.finalize()
        return self.log

    def finalize(self) -> None:
        """Emit RUN_SUMMARY once, with each patient's final state and synthetic survival."""
        if self._summarized:
            return
        self._summarized = True
        self.log.emit(self.tick, EventType.RUN_SUMMARY, "engine", {
            "end_tick": self.tick, "state_version": self.state_version,
            "patients": [{"id": p.id, "status": p.status, "hospital_id": p.hospital_id,
                          "walk_in": p.walk_in, "survival_prob": p.survival_prob,
                          "timestamps": p.timestamps.model_dump()}
                         for p in sorted(self.patients.values(), key=lambda p: p.id)],
        })

    def _fingerprint(self) -> str:
        state = {
            "hospitals": {h: (hs.config.model_dump(mode="json"), hs.occupied,
                              hs.nurses_loaned_in, hs.nurses_loaned_out, len(hs.queue),
                              len(hs.treatments))
                          for h, hs in sorted(self.hospitals.items())},
            "ambulances": {a: (x.state, x.state_until_tick, x.assigned_incident,
                               x.assigned_patient_ids, x.destination_hospital, x.location)
                           for a, x in sorted(self.ambulances.items())},
            "units": sorted(self.activated_units),
            "patients": {p: (x.status, x.ambulance_id, x.hospital_id)
                         for p, x in sorted(self.patients.items())},
            "scenes": {i: x.scene_secured for i, x in sorted(self.incidents.items())},
        }
        return hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()

    # --- observations (PLAN §11) ---------------------------------------------------------------

    def _refresh_board(self) -> None:
        self.board_tick = self.tick
        self.board = {}
        for hid, hs in sorted(self.hospitals.items()):
            self.board[hid] = {
                "free": {r: hs.free(r) for r in RESOURCES},
                "er_occupancy": round(hs.er_occupancy(), 3),
                "queue": sum(1 for q in hs.queue if not q.background),
                "boarding": len(hs.boarders),
            }

    def observe(self) -> Observation:
        """The view a dispatcher (baseline or agent) gets this tick."""
        if self.info == "complete" or self.board_tick < 0 or \
                self.tick % settings.BOARD_UPDATE_MIN == 0:
            self._refresh_board()
        partial = self.info == "partial"
        incidents: dict[str, ObsIncident] = {}
        for iid, inc in sorted(self.incidents.items()):
            if iid not in self.active_or_closed():
                continue
            victims = [self.patients[p] for p in inc.true_victim_ids]
            if iid not in self.active_incidents and not any(
                    p.status in (PatientStatus.WAITING_ON_SCENE, PatientStatus.IN_TRANSPORT)
                    for p in victims):
                continue
            reported = any(p.timestamps.unit_on_scene is not None for p in victims)
            known = not partial or reported
            patients = []
            for p in victims if known else []:
                status, amb = p.status.value, p.ambulance_id
                if partial and p.walk_in and (p.timestamps.arrived_hospital or 0) > self.board_tick:
                    status, amb = PatientStatus.WAITING_ON_SCENE.value, None  # not yet reported
                sev = p.observed_severity if partial else p.true_severity
                patients.append(ObsPatient(id=p.id, incident_id=iid, severity=sev,
                                           needs=p.needs if sev is not None else None,
                                           status=status, ambulance_id=amb))
            incidents[iid] = ObsIncident(
                id=iid, type=inc.type.value, location=inc.location, call_tick=inc.call_tick,
                reported_victims=inc.reported_victims, narrative=inc.narrative,
                violent=inc.violent, secured=inc.scene_secured,
                needs_fire=inc.needs_fire_extrication, scene_reported=reported,
                patients=patients)
        units = {a.id: ObsUnit(
            id=a.id, owner=a.owner.value, unit_type=a.unit_type.value, state=a.state.value,
            location=self.position(a.id), home=a.home_station,
            available=self.unit_available(a.id), reassignable=can_reassign(a),
            assigned_incident=a.assigned_incident, patient_ids=list(a.assigned_patient_ids),
            destination=a.destination_hospital) for a in sorted(self.ambulances.values(),
                                                                key=lambda a: a.id)}
        hospitals = {}
        for hid, hs in sorted(self.hospitals.items()):
            c, b = hs.config, self.board[hid]
            hospitals[hid] = ObsHospital(
                id=hid, name=c.name, location=c.location, owner=c.owner.value,
                capabilities=sorted(c.capabilities), stabilization_only=c.stabilization_only,
                contract=c.surge_contract.model_dump(mode="json") if c.surge_contract else None,
                totals={r: hs.total(r) for r in RESOURCES}, free=dict(b["free"]),
                er_occupancy=b["er_occupancy"], queue=b["queue"], boarding=b["boarding"],
                board_tick=self.board_tick)
        firms = {f.id: ObsFirm(id=f.id, unit_ids=list(f.unit_ids),
                               max_units=f.max_mutual_aid_units,
                               activation_minutes=f.activation_minutes,
                               in_use=self.mutual_aid_units(f.id))
                 for f in self.firms.values()}
        rejections, self._rejections = self._rejections, []
        return Observation(tick=self.tick, state_version=self.state_version, info=self.info,
                           timing=self.timing, incidents=incidents, units=units,
                           hospitals=hospitals, firms=firms, rejections=rejections,
                           surge_active=surge_active(self))

    def _drain_outbox(self, obs: Observation) -> None:
        """Log protocol messages and LLM usage the policy produced while deciding."""
        for m in obs.outbox:
            self.send(m["sender"], m["recipient"], MessageType(m["type"]), m.get("reason", ""),
                      incident_id=m.get("incident_id"), patient_ids=m.get("patient_ids"),
                      proposed_action=m.get("proposed_action"),
                      negotiation_round=m.get("negotiation_round", 0))
        for call in obs.llm_calls:
            self.log.emit(self.tick, EventType.LLM_CALL, call.get("agent", "agent"), call)
        for event in obs.events:
            self.log.emit(self.tick, EventType(event["type"]), event.get("actor", "policy"),
                          event.get("payload", {}))

    def _events_and_decisions(self) -> None:
        self._scene_events()  # 5
        self._new_calls()
        self._walk_ins()
        self._dispatch_teams()
        self._staff_loans()
        self._mutual_aid_activation()
        self._background_arrivals()
        self._close_incidents()
        if self.policy is not None:  # 6
            before = self._fingerprint()
            obs = self.observe()
            started = time.perf_counter()
            actions = self.policy.decide(obs)
            # Wall-clock decision time stays out of the deterministic log (PLAN §3.5).
            self.decision_timings.append({"tick": self.tick, "actions": len(actions),
                                          "ms": (time.perf_counter() - started) * 1000})
            if self._fingerprint() != before:
                self.log.emit(self.tick, EventType.PROPOSAL_REJECTED, self.policy.name,
                              {"rule_id": "R9", "code": "STATE_MUTATED",
                               "reason": "policy modified engine state outside commit"})
                raise R9Violation(f"{self.policy.name} mutated engine state at tick {self.tick}")
            self._drain_outbox(obs)
            for action in actions:  # 7
                self.commit(action, actor=self.policy.name)
        self._log_hospital_status()  # 8
        if self.tick_hook is not None:
            self.tick_hook(self)

    # --- step 2: units ------------------------------------------------------------------------

    def _advance_units(self) -> None:
        for amb in sorted(self.ambulances.values(), key=lambda a: a.id):
            if amb.state in MOVING and amb.id in self.legs:
                amb.location = self.legs[amb.id].position(self.tick)
            if amb.state_until_tick is None:
                # Held states, re-checked every tick.
                if amb.state == A.ON_SCENE:
                    self._finish_on_scene(amb)  # waiting for extrication
                elif amb.state == A.LOADING and not amb.assigned_patient_ids:
                    self._start_return(amb)  # loaded patients all died before routing
                elif amb.state == A.WAITING_AT_ER:
                    self._finish_offload(amb)  # crew waiting for its patients to be admitted
                continue
            if amb.state_until_tick > self.tick:
                continue
            handler = {
                A.EN_ROUTE: self._arrive_en_route,
                A.ON_SCENE: self._finish_on_scene,
                A.LOADING: self._finish_loading,
                A.TRANSPORTING: self._arrive_hospital,
                A.WAITING_AT_ER: self._finish_offload,
                A.HANDOVER: self._finish_handover,
                A.RETURNING: self._arrive_home,
            }.get(amb.state)
            if handler is not None:
                handler(amb)

    def _arrive_en_route(self, amb: Ambulance) -> None:
        leg = self.legs.pop(amb.id)
        amb.location = leg.dest
        inc = self.incidents[amb.assigned_incident]  # type: ignore[index]
        if leg.target == "staging" or not scene_entry_allowed(inc):
            if scene_entry_allowed(inc):
                self._start_leg_to_incident(amb, inc, "engine")
            else:
                transition_ambulance(amb, A.STAGING, self.tick, self.log, incident_id=inc.id)
            return
        first_unit = all(
            self.patients[p].timestamps.unit_on_scene is None for p in inc.true_victim_ids
        )
        assess = self._assessment_minutes(amb, inc)
        transition_ambulance(amb, A.ON_SCENE, self.tick, self.log, until=self.tick + assess,
                             incident_id=inc.id)
        for p in self.waiting_patients(inc.id):
            if p.timestamps.unit_on_scene is None:
                p.timestamps.unit_on_scene = self.tick
            p.observed_severity = p.true_severity
        if first_unit:
            counts = {s: 0 for s in Severity}
            for p in self.waiting_patients(inc.id):
                counts[p.true_severity] += 1
            self.log.emit(self.tick, EventType.SCENE_REPORT, amb.id,
                          {"incident_id": inc.id, "victims": sum(counts.values()),
                           "by_severity": counts, "violent": inc.violent,
                           "needs_fire": inc.needs_fire_extrication})

    def _lead_patient(self, pids: list[str]) -> Patient | None:
        pats = [self.patients[p] for p in pids]
        if not pats:
            return None
        return min(pats, key=lambda p: (SEVERITY_PRIORITY[p.true_severity], p.id))

    def _patient_minutes(self, pids: list[str], draw: str, r: tuple[int, int]) -> int:
        lead = self._lead_patient(pids)
        u = self.patient_u[lead.id][draw] if lead else None
        return self.sampler.minutes(r, u)

    def _assessment_minutes(self, amb: Ambulance, inc: Incident) -> int:
        pids = amb.assigned_patient_ids or [p.id for p in self.waiting_patients(inc.id)]
        lead = self._lead_patient(pids)
        critical = lead is not None and lead.true_severity == Severity.CRITICAL
        r = self.timing.scene_time_critical if critical else self.timing.scene_time_other
        return self._patient_minutes(pids, "scene", r)

    def _finish_on_scene(self, amb: Ambulance) -> None:
        inc = self.incidents[amb.assigned_incident]  # type: ignore[index]
        if inc.needs_fire_extrication:
            done = self.extrication_done.get(inc.id)
            if done is None or done > self.tick:
                amb.state_until_tick = None  # hold until extrication completes
                return
        alive = [p for p in amb.assigned_patient_ids
                 if self.patients[p].status == PatientStatus.WAITING_ON_SCENE]
        crew_triage = not alive
        if crew_triage:
            alive = self._crew_pick_patients(amb, inc)
        amb.assigned_patient_ids = alive
        for pid in alive:
            self.patients[pid].ambulance_id = amb.id
        if not alive:
            self._start_return(amb)
            return
        cleared = self._clear_unvalidated_destination(amb)
        transition_ambulance(amb, A.LOADING, self.tick, self.log,
                             until=self.tick + self._patient_minutes(alive, "loading",
                                                                     self.timing.loading),
                             actor="engine:crew" if crew_triage else "engine",
                             incident_id=inc.id, patient_ids=alive, crew_triage=crew_triage,
                             destination_cleared=cleared)

    def _clear_unvalidated_destination(self, amb: Ambulance) -> bool:
        """A destination stands only if it was validated for (a superset of) these patients."""
        if amb.destination_hospital is None:
            return False
        validated = self.validated_dest.get(amb.id)
        if validated and validated[1] == amb.destination_hospital and \
                set(amb.assigned_patient_ids) <= validated[0]:
            return False
        amb.destination_hospital = None
        self.validated_dest.pop(amb.id, None)
        return True

    def _crew_pick_patients(self, amb: Ambulance, inc: Incident) -> list[str]:
        """On-scene crew triage: most severe unassigned waiting patients, within R7 capacity."""
        free = sorted(
            (p for p in self.waiting_patients(inc.id) if p.ambulance_id in (None, amb.id)),
            key=lambda p: (SEVERITY_PRIORITY[p.true_severity], p.id),
        )
        if not free:
            return []
        if free[0].true_severity == Severity.CRITICAL:
            return [free[0].id]
        return [p.id for p in free if p.true_severity != Severity.CRITICAL][: amb.MAX_NON_CRITICAL]

    def _finish_loading(self, amb: Ambulance) -> None:
        amb.assigned_patient_ids = [
            p for p in amb.assigned_patient_ids
            if self.patients[p].status == PatientStatus.WAITING_ON_SCENE
        ]
        if not amb.assigned_patient_ids:
            self._start_return(amb)
            return
        if amb.destination_hospital is not None:
            self._revalidate_destination(amb)
        if amb.destination_hospital is None:
            amb.state_until_tick = None  # loaded; waiting for a destination decision
            return
        self._start_transport(amb)

    def _revalidate_destination(self, amb: Ambulance) -> None:
        """PLAN §14.1: a decision made on an older state is re-validated, not executed blindly."""
        route = RouteToHospital(unit_id=amb.id, hospital_id=amb.destination_hospital or "")
        results = self.validator.check(route, self)
        blocks = [r for r in results if r.level == "block"]
        self.commits.append({"tick": self.tick, "actor": "engine:revalidate",
                             "action": route.model_dump(mode="json"),
                             "results": [r.model_dump() for r in results],
                             "committed": not blocks})
        if blocks:
            for f in blocks:
                self.log.emit(self.tick, EventType.PROPOSAL_REJECTED, "engine:revalidate",
                              {"action": route.model_dump(mode="json"), "rule_id": f.rule_id,
                               "code": f.code, "reason": f.reason})
                self._rejections.append(Rejection(tick=self.tick,
                                                  action=route.model_dump(mode="json"),
                                                  rule_id=f.rule_id, code=f.code))
            amb.destination_hospital = None
            self.validated_dest.pop(amb.id, None)
        else:
            self.validated_dest[amb.id] = (frozenset(amb.assigned_patient_ids),
                                           route.hospital_id)

    def _start_transport(self, amb: Ambulance) -> None:
        hs = self.hospitals[amb.destination_hospital]  # type: ignore[index]
        origin = amb.location
        minutes = self.sampler.travel(origin, hs.config.location)
        self.legs[amb.id] = Leg(origin, hs.config.location, self.tick, self.tick + minutes,
                                "hospital")
        amb.onboard_patient_ids = list(amb.assigned_patient_ids)
        for pid in amb.onboard_patient_ids:
            transition_patient(self.patients[pid], PatientStatus.IN_TRANSPORT, self.tick,
                               self.log, unit_id=amb.id, hospital_id=hs.id)
        transition_ambulance(amb, A.TRANSPORTING, self.tick, self.log, until=self.tick + minutes,
                             hospital_id=hs.id, patient_ids=list(amb.onboard_patient_ids))
        severities = [self.patients[p].observed_severity for p in amb.onboard_patient_ids]
        self.send(amb.id, f"hospital:{hs.id}", MessageType.PRE_ALERT,
                  f"{len(severities)} patient(s) inbound, ETA {minutes} min",
                  incident_id=amb.assigned_incident, patient_ids=amb.onboard_patient_ids,
                  proposed_action={"eta_tick": self.tick + minutes, "severities": severities})

    def _queue_item(self, p: Patient, hospital_id: str, tick: int) -> QueueItem:
        cfg, u = self.timing, self.patient_u[p.id]
        stab = self.hospitals[hospital_id].config.stabilization_only and p.needs.trauma_bay
        er_range = cfg.er_serious if p.true_severity in (Severity.CRITICAL, Severity.SERIOUS) \
            else cfg.er_minor
        return QueueItem(
            id=p.id, severity=p.true_severity, demand=self.demand_at(hospital_id, p),
            needs_or=p.needs.or_within_minutes is not None and not stab, arrival_tick=tick,
            durations={"bay": self.sampler.minutes(cfg.trauma_bay, u["bay"]),
                       "or": self.sampler.minutes(cfg.operating_room, u["or"]),
                       "er": self.sampler.minutes(er_range, u["er"])},
            stabilization=stab,
            needs_ward=p.true_severity in (Severity.CRITICAL, Severity.SERIOUS),
        )

    def _arrive_hospital(self, amb: Ambulance) -> None:
        leg = self.legs.pop(amb.id)
        amb.location = leg.dest
        hs = self.hospitals[amb.destination_hospital]  # type: ignore[index]
        alive = [pid for pid in amb.onboard_patient_ids
                 if self.patients[pid].status == PatientStatus.IN_TRANSPORT]
        if not alive:  # every onboard patient died in transport; no offload or handover
            self._start_return(amb)
            return
        occupancy, queue_len = hs.er_occupancy(), len(hs.queue)
        for pid in alive:
            p = self.patients[pid]
            transition_patient(p, PatientStatus.WAITING_AT_ER, self.tick, self.log,
                               hospital_id=hs.id, unit_id=amb.id)
            p.hospital_id = hs.id
            hs.enqueue(self._queue_item(p, hs.id, self.tick))
        hs.ambulances_waiting.append(amb.id)
        band = self.sampler.offload_band(occupancy, queue_len, self.patient_u[alive[0]]["offload"])
        transition_ambulance(amb, A.WAITING_AT_ER, self.tick, self.log, until=self.tick + band,
                             hospital_id=hs.id, occupancy=round(occupancy, 3), band_minutes=band)

    def _finish_offload(self, amb: Ambulance) -> None:
        """The crew stays with its patients until the hospital has taken every one into care
        (PLAN §8). Minimum stay is the crowding band; there is no cap."""
        waiting = [p for p in amb.onboard_patient_ids
                   if self.patients[p].status == PatientStatus.WAITING_AT_ER]
        if waiting:
            amb.state_until_tick = None
            return
        hs = self.hospitals[amb.destination_hospital]  # type: ignore[index]
        hs.ambulances_waiting.remove(amb.id)
        transition_ambulance(amb, A.HANDOVER, self.tick, self.log,
                             until=self.tick + self._patient_minutes(
                                 amb.onboard_patient_ids, "handover", self.timing.handover),
                             hospital_id=hs.id)

    def _finish_handover(self, amb: Ambulance) -> None:
        self._start_return(amb)

    def _start_return(self, amb: Ambulance) -> None:
        origin = amb.location
        minutes = self.sampler.travel(origin, amb.home_station, emergency=False)
        self.legs[amb.id] = Leg(origin, amb.home_station, self.tick, self.tick + minutes, "home")
        amb.onboard_patient_ids = []
        amb.assigned_patient_ids = []
        amb.assigned_incident = None
        amb.destination_hospital = None
        self.validated_dest.pop(amb.id, None)
        transition_ambulance(amb, A.RETURNING, self.tick, self.log, until=self.tick + minutes)

    def _arrive_home(self, amb: Ambulance) -> None:
        self.legs.pop(amb.id, None)
        amb.location = amb.home_station
        transition_ambulance(amb, A.IDLE, self.tick, self.log)

    # --- step 2b: police / fire (rule-based) --------------------------------------------------

    def _advance_teams(self) -> None:
        for team in sorted(self.teams.values(), key=lambda t: t.id):
            if team.state in (TeamState.EN_ROUTE, TeamState.RETURNING) and team.id in self.legs:
                team.location = self.legs[team.id].position(self.tick)
            if team.state_until_tick is None or team.state_until_tick > self.tick:
                continue
            leg = self.legs.pop(team.id, None)
            if leg is not None:
                team.location = leg.dest
            if team.state == TeamState.EN_ROUTE:
                inc = self.incidents[team.assigned_incident]  # type: ignore[index]
                transition_team(team, TeamState.ON_SCENE, self.tick, self.log, incident_id=inc.id)
                if team.kind == TeamKind.POLICE and not inc.scene_secured:
                    inc.scene_secured_tick = self.tick + inc.secure_delay_min
                if team.kind == TeamKind.FIRE:
                    self.extrication_done[inc.id] = self.tick + inc.extrication_min
            elif team.state == TeamState.RETURNING:
                team.assigned_incident = None
                transition_team(team, TeamState.IDLE, self.tick, self.log)

    def _dispatch_teams(self) -> None:
        remaining = []
        for inc_id, kind in self.pending_team_requests:
            inc = self.incidents[inc_id]
            idle = [t for t in self.teams.values() if t.kind == kind and t.state in
                    (TeamState.IDLE, TeamState.RETURNING)]
            if not idle:
                remaining.append((inc_id, kind))
                continue
            team = min(idle, key=lambda t: (estimate_eta(self.position(t.id), inc.location,
                                                         self.timing)["median_min"], t.id))
            origin = self.position(team.id)
            minutes = self.sampler.travel(origin, inc.location)
            self.legs[team.id] = Leg(origin, inc.location, self.tick, self.tick + minutes, "scene")
            team.assigned_incident = inc.id
            transition_team(team, TeamState.EN_ROUTE, self.tick, self.log,
                            until=self.tick + minutes, incident_id=inc.id)
        self.pending_team_requests = remaining

    # --- step 3: hospitals --------------------------------------------------------------------

    def _hospital_flow(self) -> None:
        for hid in sorted(self.hospitals):
            hs = self.hospitals[hid]
            for pid in hs.finish_treatments(self.tick):
                transition_patient(self.patients[pid], PatientStatus.DISCHARGED, self.tick,
                                   self.log, hospital_id=hs.id)
            for pid, move in hs.last_moves:
                inc = self.patients[pid].incident_id
                reason = ("admitted to ward" if move == "ward"
                          else "boarding in ER: no ward bed free")
                self.send(f"hospital:{hs.id}", "all", MessageType.STATUS, f"{pid} {reason}",
                          incident_id=inc, patient_ids=[pid],
                          proposed_action={"move": move})
            stabilization = {q.id for q in hs.queue if q.stabilization}
            for pid in hs.admit_from_queue(self.tick):
                p = self.patients[pid]
                p.survival_prob = survival_probability(
                    p.true_severity, self.tick - p.timestamps.call, p.deterioration_rate)
                transition_patient(p, PatientStatus.IN_TREATMENT, self.tick, self.log,
                                   hospital_id=hs.id, survival_prob=round(p.survival_prob, 4),
                                   stabilization_only=pid in stabilization)

    # --- step 4: deterioration ----------------------------------------------------------------

    def _deterioration(self) -> None:
        called = self.active_or_closed()
        for p in self.patients.values():
            if p.status not in ACTIVE_PATIENT or p.incident_id not in called:
                continue
            minutes = self.tick - p.timestamps.call
            p.survival_prob = survival_probability(p.true_severity, minutes, p.deterioration_rate)
            if is_dead(p.true_severity, minutes, p.deterioration_rate):
                if p.status == PatientStatus.WAITING_AT_ER and p.hospital_id:
                    self.hospitals[p.hospital_id].remove_from_queue(p.id)
                if p.status == PatientStatus.WAITING_ON_SCENE and p.ambulance_id:
                    amb = self.ambulances[p.ambulance_id]
                    if p.id in amb.assigned_patient_ids:
                        amb.assigned_patient_ids.remove(p.id)
                # ambulance_id / hospital_id are kept on the patient as history.
                transition_patient(p, PatientStatus.DECEASED, self.tick, self.log,
                                   survival_prob=round(p.survival_prob, 4))

    def active_or_closed(self) -> set[str]:
        return set(self.active_incidents) | self.closed_incidents

    # --- step 5: events -----------------------------------------------------------------------

    def _new_calls(self) -> None:
        for inc in sorted(self.incidents.values(), key=lambda i: i.id):
            if inc.call_tick != self.tick:
                continue
            self.active_incidents[inc.id] = inc
            self.log.emit(self.tick, EventType.CALL_RECEIVED, "caller",
                          {"incident_id": inc.id, "type": inc.type, "location": inc.location,
                           "reported_victims": inc.reported_victims, "narrative": inc.narrative,
                           "violent": inc.violent})
            if inc.violent and not inc.scene_secured:
                self.pending_team_requests.append((inc.id, TeamKind.POLICE))
            if inc.needs_fire_extrication:
                self.pending_team_requests.append((inc.id, TeamKind.FIRE))

    def _scene_events(self) -> None:
        for inc_id in sorted(self.active_incidents):
            inc = self.active_incidents[inc_id]
            if inc.scene_secured or inc.scene_secured_tick is None:
                continue
            if inc.scene_secured_tick <= self.tick:
                secure_scene(inc, self.tick, self.log, actor="police")
                for amb in sorted(self.ambulances.values(), key=lambda a: a.id):
                    if amb.assigned_incident != inc.id:
                        continue
                    staging_leg = amb.state == A.EN_ROUTE and self.legs[amb.id].target == "staging"
                    if amb.state == A.STAGING or staging_leg:
                        self._start_leg_to_incident(amb, inc, "engine")

    def _walk_ins(self) -> None:
        for w in self.walk_ins:
            if w.tick != self.tick:
                continue
            p = self.patients[w.patient_id]
            if p.status != PatientStatus.WAITING_ON_SCENE or p.ambulance_id is not None:
                continue
            hs = self.hospitals[w.hospital_id]
            p.walk_in = True
            p.hospital_id = hs.id
            transition_patient(p, PatientStatus.WAITING_AT_ER, self.tick, self.log,
                               hospital_id=hs.id, walk_in=True)
            hs.enqueue(self._queue_item(p, hs.id, self.tick))
            self.log.emit(self.tick, EventType.WALK_IN, f"hospital:{hs.id}",
                          {"patient_id": p.id, "hospital_id": hs.id, "incident_id": p.incident_id})

    def _staff_loans(self) -> None:
        kept = []
        for loan in self.loans:
            borrower = self.hospitals[loan.borrower]
            slots = loan.nurses * PATIENTS_PER_NURSE
            if loan.phase == "DEPARTED" and loan.arrive_tick <= self.tick:
                loan.phase = "ARRIVED"
                borrower.nurses_loaned_in += loan.nurses
                self._log_loan(loan, "ARRIVED")
            if loan.phase == "ARRIVED" and loan.return_tick <= self.tick:
                # Due back: the borrower may not admit into these nurses' slots any more.
                loan.phase = "RETURNING"
                borrower.nurse_slots_held_back += slots
            if loan.phase == "RETURNING" and borrower.free("nurse_slot") >= slots:
                borrower.nurse_slots_held_back -= slots
                borrower.nurses_loaned_in -= loan.nurses
                self.hospitals[loan.lender].nurses_loaned_out -= loan.nurses
                self._log_loan(loan, "RETURNED")
                continue
            kept.append(loan)
        self.loans = kept

    def _log_loan(self, loan: StaffLoan, phase: str) -> None:
        self.log.emit(self.tick, EventType.STAFF_LOAN, "engine",
                      {"lender": loan.lender, "borrower": loan.borrower, "nurses": loan.nurses,
                       "phase": phase})

    def _mutual_aid_activation(self) -> None:
        remaining = []
        for firm_id, n, ready in self.pending_mutual_aid:
            if ready > self.tick:
                remaining.append((firm_id, n, ready))
                continue
            firm = self.firms[firm_id]
            new = [u for u in sorted(firm.unit_ids) if u not in self.activated_units][:n]
            self.activated_units.update(new)
            self.send(f"firm:{firm_id}", "all", MessageType.STATUS,
                      f"units activated: {', '.join(new) or 'none'}",
                      proposed_action={"units_activated": new})
        self.pending_mutual_aid = remaining

    def _background_arrivals(self) -> None:
        if self.tick == 0:
            return
        bg = self.sampler.stream("background")
        for hid in sorted(self._bg_rate):
            rate = self._bg_rate[hid]
            if rate <= 0:
                continue
            for _ in range(int(bg.poisson(rate))):
                stay = self.sampler.minutes(self.timing.er_background, float(bg.random()))
                self.hospitals[hid].add_background_patient(self.tick, stay, in_treatment=False)
        for hid in sorted(self._ward_rate):
            rate = self._ward_rate[hid]
            if rate <= 0:
                continue
            for _ in range(int(bg.poisson(rate))):  # direct / elective admissions
                stay = self.sampler.minutes(self.timing.ward_stay, float(bg.random()))
                self.hospitals[hid].add_background_ward_patient(self.tick, stay)

    def _close_incidents(self) -> None:
        for inc_id in sorted(self.active_incidents):
            if self.waiting_patients(inc_id):
                continue
            if any(a.assigned_incident == inc_id and a.state in (A.EN_ROUTE, A.STAGING,
                                                                A.ON_SCENE, A.LOADING)
                   for a in self.ambulances.values()):
                continue
            inc = self.active_incidents.pop(inc_id)
            self.closed_incidents.add(inc_id)
            for team in sorted(self.teams.values(), key=lambda t: t.id):
                if team.assigned_incident == inc_id and team.state in (TeamState.ON_SCENE,
                                                                       TeamState.EN_ROUTE):
                    origin = self.position(team.id)
                    minutes = self.sampler.travel(origin, team.home, emergency=False)
                    self.legs[team.id] = Leg(origin, team.home, self.tick, self.tick + minutes,
                                             "home")
                    transition_team(team, TeamState.RETURNING, self.tick, self.log,
                                    until=self.tick + minutes)
            self.pending_team_requests = [r for r in self.pending_team_requests
                                          if r[0] != inc.id]

    # --- step 8 -------------------------------------------------------------------------------

    def _log_hospital_status(self) -> None:
        for hid in sorted(self.hospitals):
            snap = self.hospitals[hid].snapshot()
            if snap != self._last_status.get(hid):
                self._last_status[hid] = snap
                self.log.emit(self.tick, EventType.HOSPITAL_STATUS, f"hospital:{hid}", snap)
