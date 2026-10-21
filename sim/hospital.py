"""Hospital capacity accounting, ER queue, treatment, and staff loans (PLAN §8).

Resources: ER beds, trauma bays, operating rooms, trauma surgeons, and nurse slots. Each nurse
covers `PATIENTS_PER_NURSE` patients; a critical patient takes two slots (one dedicated nurse).
Background (non-scenario) patients are anonymous queue/treatment entries with id `BG-...`.

Treatment durations are carried on each queue item (drawn by the engine from per-patient or
background streams), so the hospital itself consumes no randomness.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from sim.entities import Hospital, PatientNeeds, Severity

PATIENTS_PER_NURSE = 2
RESOURCES = ("er_bed", "trauma_bay", "or", "surgeon", "nurse_slot")
SEVERITY_PRIORITY = {
    Severity.CRITICAL: 0,
    Severity.SERIOUS: 1,
    Severity.MINOR: 2,
    Severity.EXPECTANT: 3,
}


def resource_demand(
    needs: PatientNeeds, severity: Severity, *, stabilization_only: bool = False
) -> dict[str, int]:
    """Resources required at admission. The OR is taken later, after the trauma-bay phase.

    At a stabilization-only hospital (Hospital B) a trauma patient uses the bay and a dedicated
    nurse but no surgeon or OR (R3 decides when that is allowed).
    """
    d = {r: 0 for r in RESOURCES}
    d["er_bed"] = int(needs.er_bed)
    d["trauma_bay"] = int(needs.trauma_bay)
    d["surgeon"] = int(needs.trauma_surgeon and not stabilization_only)
    if needs.nurse:
        d["nurse_slot"] = 2 if severity == Severity.CRITICAL else 1
    return d


class QueueItem(BaseModel):
    id: str
    severity: Severity
    demand: dict[str, int]
    needs_or: bool = False
    arrival_tick: int
    seq: int = 0  # arrival order; set by `enqueue`, breaks priority ties
    durations: dict[str, int]  # "bay", "or", "er" minutes as applicable
    background: bool = False
    stabilization: bool = False


class Treatment(BaseModel):
    id: str
    severity: Severity
    held: dict[str, int]
    phase: str  # "bay" | "or" | "er"
    end_tick: int | None  # None while waiting in a bay for an OR
    needs_or: bool = False
    or_minutes: int = 0
    background: bool = False


class HospitalState(BaseModel):
    config: Hospital
    occupied: dict[str, int] = Field(default_factory=lambda: {r: 0 for r in RESOURCES})
    nurses_loaned_out: int = 0
    nurses_loaned_in: int = 0
    nurse_slots_held_back: int = 0  # slots of borrowed nurses due back; not usable for admission
    queue: list[QueueItem] = Field(default_factory=list)
    treatments: list[Treatment] = Field(default_factory=list)
    ambulances_waiting: list[str] = Field(default_factory=list)
    background_seq: int = 0
    arrival_seq: int = 0

    # --- capacity -----------------------------------------------------------------------------

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def effective_nurses(self) -> int:
        return self.config.nurses_total - self.nurses_loaned_out + self.nurses_loaned_in

    def total(self, resource: str) -> int:
        c = self.config
        return {
            "er_bed": c.er_beds_total,
            "trauma_bay": c.trauma_bays_total,
            "or": c.ors_total,
            "surgeon": c.trauma_surgeons_total,
            "nurse_slot": self.effective_nurses * PATIENTS_PER_NURSE,
        }[resource]

    def free(self, resource: str) -> int:
        return self.total(resource) - self.occupied[resource]

    def admissible_free(self, resource: str) -> int:
        held_back = self.nurse_slots_held_back if resource == "nurse_slot" else 0
        return self.free(resource) - held_back

    def fits(self, demand: dict[str, int], reserved: dict[str, int] | None = None) -> bool:
        reserved = reserved or {}
        return all(
            self.admissible_free(r) - reserved.get(r, 0) >= n for r, n in demand.items()
        )

    def has_resource_types(self, demand: dict[str, int]) -> bool:
        return all(self.total(r) > 0 for r, n in demand.items() if n > 0)

    def er_occupancy(self) -> float:
        queued_beds = sum(q.demand["er_bed"] for q in self.queue)
        return (self.occupied["er_bed"] + queued_beds) / max(1, self.config.er_beds_total)

    def or_available_by(self, at_tick: int) -> bool:
        freeing = sum(1 for t in self.treatments
                      if t.phase == "or" and t.end_tick is not None and t.end_tick <= at_tick)
        return self.free("or") + freeing > 0

    def projected_free(self, resource: str, at_tick: int, incoming: list[dict[str, int]]) -> int:
        """Free units of `resource` at `at_tick`, counting scheduled releases, the current queue,
        and already-committed incoming patients.

        A trauma-bay phase that continues into the OR releases only the bay (and only if an OR
        is projected free); its surgeon and nurse slots stay held through surgery.
        """
        releasing = 0
        for t in self.treatments:
            if t.end_tick is None or t.end_tick > at_tick:
                continue
            if t.phase == "bay" and t.needs_or:
                if resource == "trauma_bay" and self.or_available_by(at_tick):
                    releasing += t.held.get("trauma_bay", 0)
                continue
            releasing += t.held.get(resource, 0)
        queued = sum(q.demand.get(resource, 0) for q in self.queue)
        committed = sum(d.get(resource, 0) for d in incoming)
        held_back = self.nurse_slots_held_back if resource == "nurse_slot" else 0
        return self.free(resource) - held_back + releasing - queued - committed

    def can_accept(
        self, demand: dict[str, int], at_tick: int, incoming: list[dict[str, int]]
    ) -> bool:
        return all(
            self.projected_free(r, at_tick, incoming) >= n for r, n in demand.items() if n > 0
        )

    def earliest_fit(
        self, demand: dict[str, int], from_tick: int, incoming: list[dict[str, int]]
    ) -> int | None:
        """First tick >= from_tick at which `demand` is projected to fit (None if never, given
        currently scheduled releases)."""
        candidates = sorted({from_tick} | {
            t.end_tick for t in self.treatments if t.end_tick is not None and t.end_tick > from_tick
        })
        for tick in candidates:
            if self.can_accept(demand, tick, incoming):
                return tick
        return None

    # --- flow ---------------------------------------------------------------------------------

    def enqueue(self, item: QueueItem) -> None:
        self.arrival_seq += 1
        self.queue.append(item.model_copy(update={"seq": self.arrival_seq}))

    def remove_from_queue(self, item_id: str) -> bool:
        before = len(self.queue)
        self.queue = [q for q in self.queue if q.id != item_id]
        return len(self.queue) < before

    def _hold(self, demand: dict[str, int]) -> None:
        for r, n in demand.items():
            self.occupied[r] += n

    def _release(self, held: dict[str, int]) -> None:
        for r, n in held.items():
            self.occupied[r] -= n

    def admit_from_queue(self, tick: int) -> list[str]:
        """Admit queued patients in priority order. A higher-priority patient who does not fit
        reserves whatever free resources it needs, so lower-priority patients cannot starve it.
        Returns ids of admitted scenario (non-background) patients."""
        admitted: list[str] = []
        reserved = {r: 0 for r in RESOURCES}
        order = sorted(self.queue, key=lambda q: (SEVERITY_PRIORITY[q.severity], q.seq))
        for item in order:
            if not self.fits(item.demand, reserved):
                for r, n in item.demand.items():
                    avail = max(0, self.admissible_free(r) - reserved[r])
                    reserved[r] += min(n, avail)
                continue
            self._hold(item.demand)
            if item.demand["trauma_bay"]:
                phase, minutes = "bay", item.durations["bay"]
            else:
                phase, minutes = "er", item.durations["er"]
            self.treatments.append(Treatment(
                id=item.id, severity=item.severity, held=dict(item.demand), phase=phase,
                end_tick=tick + minutes, needs_or=item.needs_or,
                or_minutes=item.durations.get("or", 0), background=item.background,
            ))
            self.remove_from_queue(item.id)
            if not item.background:
                admitted.append(item.id)
        return admitted

    def finish_treatments(self, tick: int) -> list[str]:
        """Advance treatment phases; returns ids of discharged scenario patients."""
        discharged: list[str] = []
        still: list[Treatment] = []
        for t in self.treatments:
            if t.end_tick is not None and t.end_tick > tick:
                still.append(t)
                continue
            if t.phase == "bay" and t.needs_or:
                # Move from trauma bay to OR when one is free; otherwise keep holding the bay.
                if self.free("or") >= 1:
                    self.occupied["trauma_bay"] -= t.held["trauma_bay"]
                    t.held["trauma_bay"] = 0
                    self.occupied["or"] += 1
                    t.held["or"] = 1
                    t.phase = "or"
                    t.end_tick = tick + t.or_minutes
                else:
                    t.end_tick = None
                still.append(t)
                continue
            self._release(t.held)
            if not t.background:
                discharged.append(t.id)
        self.treatments = still
        return discharged

    def add_background_patient(
        self, tick: int, stay: int, *, in_treatment: bool, remaining: int | None = None
    ) -> None:
        self.background_seq += 1
        item = QueueItem(
            id=f"BG-{self.id}-{self.background_seq}",
            severity=Severity.MINOR,
            demand={"er_bed": 1, "trauma_bay": 0, "or": 0, "surgeon": 0, "nurse_slot": 1},
            arrival_tick=tick,
            durations={"er": stay},
            background=True,
        )
        if in_treatment:
            self._hold(item.demand)
            self.treatments.append(Treatment(
                id=item.id, severity=item.severity, held=dict(item.demand), phase="er",
                end_tick=tick + (remaining if remaining is not None else stay), background=True,
            ))
        else:
            self.enqueue(item)

    # --- staff loans --------------------------------------------------------------------------

    def can_lend(self, n: int) -> bool:
        """R8: own nurses only (borrowed nurses cannot be lent on); the lender stays at or above
        `min_nurse_coverage` and strands no current patient."""
        own_after = self.config.nurses_total - self.nurses_loaned_out - n
        return (
            n > 0
            and own_after >= self.config.min_nurse_coverage
            and self.admissible_free("nurse_slot") >= n * PATIENTS_PER_NURSE
        )

    def snapshot(self) -> dict:
        return {
            "hospital_id": self.id,
            "occupied": dict(self.occupied),
            "totals": {r: self.total(r) for r in RESOURCES},
            "queue": len(self.queue),
            "queue_scenario": sum(1 for q in self.queue if not q.background),
            "ambulances_waiting": len(self.ambulances_waiting),
            "er_occupancy": round(self.er_occupancy(), 3),
            "nurses_loaned_in": self.nurses_loaned_in,
            "nurses_loaned_out": self.nurses_loaned_out,
        }
