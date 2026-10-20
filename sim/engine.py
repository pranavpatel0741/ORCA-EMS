"""Deterministic tick loop and commit API (PLAN §3, §15 M2).

The engine is the only source of truth. Policies propose `Action`s; the engine validates and
commits them. Tick order (one tick = one simulated minute):

  1. advance clock
  2. complete unit transitions and move units
  3. finish treatments, release resources, admit from ER queues
  4. patient deterioration and outcome updates
  5. new incidents, walk-ins, scene events, staff loans, background arrivals
  6. collect decisions from the active policy
  7. validate and commit
  8. log hospital status changes; run invariant hook
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

import numpy as np

from sim.actions import Action, Dispatch, LendStaff, RouteToHospital
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
    SEVERITY_PRIORITY,
    HospitalState,
    QueueItem,
    resource_demand,
)
from sim.outcomes import is_dead, survival_probability
from sim.state_machine import (
    secure_scene,
    transition_ambulance,
    transition_patient,
    transition_team,
)
from sim.travel import Sampler, TimingConfig, estimate_eta, interpolate, offset_point
from sim.validator import Validator, has_capability

A = AmbulanceState
MOVING = {A.EN_ROUTE, A.TRANSPORTING, A.RETURNING}
ACTIVE_PATIENT = {PatientStatus.WAITING_ON_SCENE, PatientStatus.IN_TRANSPORT,
                  PatientStatus.WAITING_AT_ER}


class Policy(Protocol):
    name: str

    def decide(self, engine: Engine) -> list[Action]: ...


class Leg:
    """A straight-line movement between two points over [start, end] ticks."""

    __slots__ = ("origin", "dest", "start", "end", "target")

    def __init__(self, origin: Location, dest: Location, start: int, end: int, target: str):
        self.origin, self.dest, self.start, self.end, self.target = origin, dest, start, end, target

    def position(self, tick: int) -> Location:
        span = max(1, self.end - self.start)
        return interpolate(self.origin, self.dest, (tick - self.start) / span)


class StaffLoan:
    __slots__ = ("lender", "borrower", "nurses", "arrive_tick", "return_tick", "arrived")

    def __init__(self, lender: str, borrower: str, nurses: int, arrive_tick: int, return_tick: int):
        self.lender, self.borrower, self.nurses = lender, borrower, nurses
        self.arrive_tick, self.return_tick, self.arrived = arrive_tick, return_tick, False


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
    ) -> None:
        self.scenario = scenario
        self.policy = policy
        self.timing = timing or TimingConfig()
        self.validator = validator or Validator()
        self.rng = np.random.default_rng([scenario.seed, 1])
        self.sampler = Sampler(self.rng, self.timing)
        self.run_id = run_id or f"s{scenario.seed:02d}_{scenario.demand}_{scenario.info}_" + (
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

        self.tick = 0
        self.state_version = 0
        self.active_incidents: dict[str, Incident] = {}
        self.closed_incidents: set[str] = set()
        self.legs: dict[str, Leg] = {}
        self.activated_units: set[str] = {
            a.id for a in sc.ambulances if a.owner == Owner.PUBLIC
        }
        self.pending_team_requests: list[tuple[str, TeamKind]] = []
        self.extrication_done: dict[str, int] = {}
        self.loans: list[StaffLoan] = []
        self.committed_units_this_tick: set[str] = set()
        self.commits: list[dict[str, Any]] = []
        self._last_status: dict[str, dict] = {}
        self._bg_rate: dict[str, float] = {}
        self._initialized = False

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

    def incoming_demands(self, hospital_id: str, exclude: set[str] | None = None) -> list[dict]:
        """Resource demand of patients committed to `hospital_id` but not yet arrived."""
        exclude = exclude or set()
        out = []
        for amb in self.ambulances.values():
            if amb.destination_hospital != hospital_id:
                continue
            for pid in amb.assigned_patient_ids:
                p = self.patients[pid]
                if pid in exclude or p.status not in (
                    PatientStatus.WAITING_ON_SCENE, PatientStatus.IN_TRANSPORT
                ):
                    continue
                out.append(resource_demand(p.needs, p.true_severity))
        return out

    def structurally_capable(self, hospital_id: str, patients: list[Patient]) -> bool:
        hs = self.hospitals[hospital_id]
        return all(
            has_capability(hs.config.capabilities, p.needs.capability)
            and hs.has_resource_types(resource_demand(p.needs, p.true_severity))
            for p in patients
        )

    def eta_tick_for(self, action: Action, hospital_id: str) -> int:
        """Expected arrival tick at `hospital_id` for the unit in `action` (median estimate)."""
        hloc = self.hospitals[hospital_id].config.location
        if isinstance(action, Dispatch):
            inc = self.incidents[action.incident_id]
            to_scene = estimate_eta(self.position(action.unit_id), inc.location, self.timing)
            on_scene = self.timing.scene_time_other[0] + self.timing.loading[0]
            to_hosp = estimate_eta(inc.location, hloc, self.timing)
            return self.tick + round(to_scene["median_min"] + on_scene + to_hosp["median_min"])
        amb = self.ambulances[action.unit_id]
        remaining = 0
        if amb.state == A.LOADING and amb.state_until_tick is not None:
            remaining = max(0, amb.state_until_tick - self.tick)
        elif amb.state == A.ON_SCENE:
            left = (amb.state_until_tick or self.tick) - self.tick
            remaining = self.timing.loading[0] + max(0, left)
        to_hosp = estimate_eta(self.position(amb.id), hloc, self.timing)
        return self.tick + remaining + round(to_hosp["median_min"])

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
        failures = [r for r in results if not r.ok]
        record = {"tick": self.tick, "actor": actor, "action": action.model_dump(mode="json"),
                  "results": [r.model_dump() for r in results], "committed": not failures}
        self.commits.append(record)
        if failures:
            for f in failures:
                self.log.emit(self.tick, EventType.PROPOSAL_REJECTED, actor,
                              {"action": record["action"], "rule_id": f.rule_id,
                               "reason": f.reason})
            return False
        notes = [r.reason for r in results if r.reason]
        self.log.emit(self.tick, EventType.PROPOSAL_VALIDATED, actor,
                      {"action": record["action"], "notes": notes})
        self._apply(action, actor)
        self.state_version += 1
        self.log.emit(self.tick, EventType.COMMITTED, actor,
                      {"action": record["action"], "state_version": self.state_version})
        return True

    def _apply(self, action: Action, actor: str) -> None:
        if isinstance(action, Dispatch):
            self._apply_dispatch(action, actor)
        elif isinstance(action, RouteToHospital):
            self._apply_route(action, actor)
        elif isinstance(action, LendStaff):
            self._apply_loan(action, actor)

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
        for pid in action.patient_ids:
            self.patients[pid].ambulance_id = amb.id
        self._start_leg_to_incident(amb, inc, actor)

    def _start_leg_to_incident(self, amb: Ambulance, inc: Incident, actor: str) -> None:
        origin = self.position(amb.id)
        if inc.violent and not inc.scene_secured:
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
        if amb.state == A.LOADING and amb.state_until_tick is None:
            self._start_transport(amb)

    def _apply_loan(self, action: LendStaff, actor: str) -> None:
        lender = self.hospitals[action.lender_id]
        lender.nurses_loaned_out += action.nurses
        arrive = self.tick + self.sampler.minutes(self.timing.staff_transfer)
        loan = StaffLoan(action.lender_id, action.borrower_id, action.nurses, arrive,
                         arrive + self.timing.staff_loan_duration)
        self.loans.append(loan)
        self.log.emit(self.tick, EventType.STAFF_LOAN, actor,
                      {"lender": loan.lender, "borrower": loan.borrower, "nurses": loan.nurses,
                       "arrive_tick": loan.arrive_tick, "return_tick": loan.return_tick,
                       "phase": "DEPARTED"})

    # ==========================================================================================
    # Tick loop
    # ==========================================================================================

    @property
    def end_tick(self) -> int:
        return self.scenario.horizon + self.scenario.drain_min

    def initialize(self) -> None:
        """Set up initial hospital load and process tick 0 (steps 5–8)."""
        for hid, frac in self.scenario.initial_occupancy.items():
            hs = self.hospitals[hid]
            n = round(frac * hs.config.er_beds_total)
            lo, hi = self.timing.er_background
            for _ in range(n):
                remaining = self.sampler.minutes((1, hi))
                hs.add_background_patient(0, self.sampler, in_treatment=True, remaining=remaining)
            mean = (lo + hi) / 2
            self._bg_rate[hid] = n / mean if self.scenario.background_arrivals else 0.0
        for amb in self.ambulances.values():
            if amb.state in MOVING and amb.state_until_tick is not None and amb.id not in self.legs:
                self.legs[amb.id] = Leg(amb.location, amb.home_station, 0, amb.state_until_tick,
                                        "home")
        self._initialized = True
        self._events_and_decisions()

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
        until = self.end_tick if until is None else until
        if not self._initialized:
            self.initialize()
        while self.tick < until:
            self.step()
        self.log.emit(self.tick, EventType.RUN_SUMMARY, "engine",
                      {"end_tick": self.tick, "state_version": self.state_version,
                       "patients": {s: sum(1 for p in self.patients.values() if p.status == s)
                                    for s in PatientStatus}})
        return self.log

    def _events_and_decisions(self) -> None:
        self._scene_events()  # 5
        self._new_calls()
        self._walk_ins()
        self._dispatch_teams()
        self._staff_loans()
        self._background_arrivals()
        self._close_incidents()
        if self.policy is not None:  # 6
            for action in self.policy.decide(self):  # 7
                self.commit(action, actor=self.policy.name)
        self._log_hospital_status()  # 8
        if self.tick_hook is not None:
            self.tick_hook(self)

    # --- step 2: units ------------------------------------------------------------------------

    def _advance_units(self) -> None:
        for amb in sorted(self.ambulances.values(), key=lambda a: a.id):
            if amb.state in MOVING and amb.id in self.legs:
                amb.location = self.legs[amb.id].position(self.tick)
            if amb.state == A.ON_SCENE and amb.state_until_tick is None:
                self._finish_on_scene(amb)  # was waiting for extrication
                continue
            if amb.state == A.LOADING and amb.state_until_tick is None:
                if not amb.assigned_patient_ids:  # loaded patients all died before routing
                    self._start_return(amb)
                continue
            if amb.state_until_tick is None or amb.state_until_tick > self.tick:
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
        if leg.target == "staging":
            if inc.scene_secured:
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

    def _assessment_minutes(self, amb: Ambulance, inc: Incident) -> int:
        pats = [self.patients[p] for p in amb.assigned_patient_ids] or self.waiting_patients(inc.id)
        critical = any(p.true_severity == Severity.CRITICAL for p in pats)
        r = self.timing.scene_time_critical if critical else self.timing.scene_time_other
        return self.sampler.minutes(r)

    def _finish_on_scene(self, amb: Ambulance) -> None:
        inc = self.incidents[amb.assigned_incident]  # type: ignore[index]
        if inc.needs_fire_extrication:
            done = self.extrication_done.get(inc.id)
            if done is None or done > self.tick:
                amb.state_until_tick = None  # hold until extrication completes
                return
        alive = [p for p in amb.assigned_patient_ids
                 if self.patients[p].status == PatientStatus.WAITING_ON_SCENE]
        if not alive:
            alive = self._crew_pick_patients(amb, inc)
        amb.assigned_patient_ids = alive
        for pid in alive:
            self.patients[pid].ambulance_id = amb.id
        if not alive:
            self._start_return(amb)
            return
        transition_ambulance(amb, A.LOADING, self.tick, self.log,
                             until=self.tick + self.sampler.minutes(self.timing.loading),
                             incident_id=inc.id, patient_ids=alive)

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
        if amb.destination_hospital is None:
            amb.state_until_tick = None  # loaded; waiting for a destination decision
            return
        self._start_transport(amb)

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
        self.log.emit(self.tick, EventType.MESSAGE, amb.id,
                      {"type": "PRE_ALERT", "recipient": f"hospital:{hs.id}",
                       "patient_ids": list(amb.onboard_patient_ids),
                       "eta_tick": self.tick + minutes,
                       "severities": [self.patients[p].observed_severity
                                      for p in amb.onboard_patient_ids]})

    def _arrive_hospital(self, amb: Ambulance) -> None:
        leg = self.legs.pop(amb.id)
        amb.location = leg.dest
        hs = self.hospitals[amb.destination_hospital]  # type: ignore[index]
        occupancy, queue_len = hs.er_occupancy(), len(hs.queue)
        for pid in amb.onboard_patient_ids:
            p = self.patients[pid]
            if p.status != PatientStatus.IN_TRANSPORT:
                continue
            transition_patient(p, PatientStatus.WAITING_AT_ER, self.tick, self.log,
                               hospital_id=hs.id, unit_id=amb.id)
            p.hospital_id = hs.id
            hs.enqueue(QueueItem(
                id=p.id, severity=p.true_severity,
                demand=resource_demand(p.needs, p.true_severity),
                needs_or=p.needs.or_within_minutes is not None, arrival_tick=self.tick,
            ))
        hs.ambulances_waiting.append(amb.id)
        wait = self.sampler.offload(occupancy, queue_len)
        transition_ambulance(amb, A.WAITING_AT_ER, self.tick, self.log, until=self.tick + wait,
                             hospital_id=hs.id, occupancy=round(occupancy, 3))

    def _finish_offload(self, amb: Ambulance) -> None:
        hs = self.hospitals[amb.destination_hospital]  # type: ignore[index]
        hs.ambulances_waiting.remove(amb.id)
        transition_ambulance(amb, A.HANDOVER, self.tick, self.log,
                             until=self.tick + self.sampler.minutes(self.timing.handover),
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
        for hs in self.hospitals.values():
            for pid in hs.finish_treatments(self.tick, self.sampler):
                transition_patient(self.patients[pid], PatientStatus.DISCHARGED, self.tick,
                                   self.log, hospital_id=hs.id)
            for pid in hs.admit_from_queue(self.tick, self.sampler):
                p = self.patients[pid]
                p.survival_prob = survival_probability(
                    p.true_severity, self.tick - p.timestamps.call, p.deterioration_rate)
                transition_patient(p, PatientStatus.IN_TREATMENT, self.tick, self.log,
                                   hospital_id=hs.id)

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
                transition_patient(p, PatientStatus.DECEASED, self.tick, self.log)

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
        for inc in list(self.active_incidents.values()):
            if inc.scene_secured or inc.scene_secured_tick is None:
                continue
            if inc.scene_secured_tick <= self.tick:
                secure_scene(inc, self.tick, self.log, actor="police")
                for amb in sorted(self.ambulances.values(), key=lambda a: a.id):
                    if amb.state == A.STAGING and amb.assigned_incident == inc.id:
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
            hs.enqueue(QueueItem(id=p.id, severity=p.true_severity,
                                 demand=resource_demand(p.needs, p.true_severity),
                                 arrival_tick=self.tick))
            self.log.emit(self.tick, EventType.WALK_IN, f"hospital:{hs.id}",
                          {"patient_id": p.id, "hospital_id": hs.id, "incident_id": p.incident_id})

    def _staff_loans(self) -> None:
        for loan in self.loans:
            if not loan.arrived and loan.arrive_tick <= self.tick:
                loan.arrived = True
                self.hospitals[loan.borrower].nurses_loaned_in += loan.nurses
                self.log.emit(self.tick, EventType.STAFF_LOAN, "engine",
                              {"lender": loan.lender, "borrower": loan.borrower,
                               "nurses": loan.nurses, "phase": "ARRIVED"})
        kept = []
        for loan in self.loans:
            borrower = self.hospitals[loan.borrower]
            needed = loan.nurses * PATIENTS_PER_NURSE
            due = loan.arrived and loan.return_tick <= self.tick
            if due and borrower.free("nurse_slot") >= needed:
                borrower.nurses_loaned_in -= loan.nurses
                self.hospitals[loan.lender].nurses_loaned_out -= loan.nurses
                self.log.emit(self.tick, EventType.STAFF_LOAN, "engine",
                              {"lender": loan.lender, "borrower": loan.borrower,
                               "nurses": loan.nurses, "phase": "RETURNED"})
            else:
                kept.append(loan)
        self.loans = kept

    def _background_arrivals(self) -> None:
        if self.tick == 0:
            return
        for hid in sorted(self._bg_rate):
            rate = self._bg_rate[hid]
            if rate <= 0:
                continue
            for _ in range(int(self.rng.poisson(rate))):
                self.hospitals[hid].add_background_patient(self.tick, self.sampler,
                                                           in_treatment=False)

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
