"""Hospital capacity accounting, ER queue, treatment, and staff loans (PLAN §8).

Resources: ER beds, trauma bays, operating rooms, trauma surgeons, and nurse slots. Each nurse
covers `PATIENTS_PER_NURSE` patients; a critical patient takes two slots (one dedicated nurse).
Background (non-scenario) patients are anonymous queue/treatment entries with id `BG-...`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from sim.entities import Hospital, PatientNeeds, Severity
from sim.travel import Sampler

PATIENTS_PER_NURSE = 2
RESOURCES = ("er_bed", "trauma_bay", "or", "surgeon", "nurse_slot")
SEVERITY_PRIORITY = {
    Severity.CRITICAL: 0,
    Severity.SERIOUS: 1,
    Severity.MINOR: 2,
    Severity.EXPECTANT: 3,
}


def resource_demand(needs: PatientNeeds, severity: Severity) -> dict[str, int]:
    """Resources required at admission. The OR is taken later, after the trauma-bay phase."""
    d = {r: 0 for r in RESOURCES}
    d["er_bed"] = int(needs.er_bed)
    d["trauma_bay"] = int(needs.trauma_bay)
    d["surgeon"] = int(needs.trauma_surgeon)
    if needs.nurse:
        d["nurse_slot"] = 2 if severity == Severity.CRITICAL else 1
    return d


class QueueItem(BaseModel):
    id: str
    severity: Severity
    demand: dict[str, int]
    needs_or: bool = False
    arrival_tick: int
    background: bool = False


class Treatment(BaseModel):
    id: str
    severity: Severity
    held: dict[str, int]
    phase: str  # "bay" | "or" | "er"
    end_tick: int | None  # None while waiting in a bay for an OR
    needs_or: bool = False
    background: bool = False


class HospitalState(BaseModel):
    config: Hospital
    occupied: dict[str, int] = Field(default_factory=lambda: {r: 0 for r in RESOURCES})
    nurses_loaned_out: int = 0
    nurses_loaned_in: int = 0
    queue: list[QueueItem] = Field(default_factory=list)
    treatments: list[Treatment] = Field(default_factory=list)
    ambulances_waiting: list[str] = Field(default_factory=list)
    surge_patients_admitted: int = 0
    background_seq: int = 0

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

    def fits(self, demand: dict[str, int]) -> bool:
        return all(self.free(r) >= n for r, n in demand.items())

    def has_resource_types(self, demand: dict[str, int]) -> bool:
        return all(self.total(r) > 0 for r, n in demand.items() if n > 0)

    def er_occupancy(self) -> float:
        queued_beds = sum(q.demand["er_bed"] for q in self.queue)
        return (self.occupied["er_bed"] + queued_beds) / max(1, self.config.er_beds_total)

    def projected_free(self, resource: str, at_tick: int, incoming: list[dict[str, int]]) -> int:
        """Free units of `resource` at `at_tick`, counting scheduled releases, the current queue,
        and already-committed incoming patients."""
        releasing = sum(
            t.held.get(resource, 0)
            for t in self.treatments
            if t.end_tick is not None and t.end_tick <= at_tick
        )
        queued = sum(q.demand.get(resource, 0) for q in self.queue)
        committed = sum(d.get(resource, 0) for d in incoming)
        return self.free(resource) + releasing - queued - committed

    def can_accept(
        self, demand: dict[str, int], at_tick: int, incoming: list[dict[str, int]]
    ) -> bool:
        return all(
            self.projected_free(r, at_tick, incoming) >= n for r, n in demand.items() if n > 0
        )

    # --- flow ---------------------------------------------------------------------------------

    def enqueue(self, item: QueueItem) -> None:
        self.queue.append(item)

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

    def _duration(self, item: QueueItem, sampler: Sampler) -> tuple[str, int]:
        cfg = sampler.cfg
        if item.demand["trauma_bay"]:
            return "bay", sampler.minutes(cfg.trauma_bay)
        if item.background:
            return "er", sampler.minutes(cfg.er_background)
        if item.severity in (Severity.CRITICAL, Severity.SERIOUS):
            return "er", sampler.minutes(cfg.er_serious)
        return "er", sampler.minutes(cfg.er_minor)

    def admit_from_queue(self, tick: int, sampler: Sampler) -> list[str]:
        """Admit queued patients in priority order (no head-of-line blocking).
        Returns ids of admitted scenario (non-background) patients."""
        admitted: list[str] = []
        order = sorted(
            self.queue, key=lambda q: (SEVERITY_PRIORITY[q.severity], q.arrival_tick, q.id)
        )
        for item in order:
            if not self.fits(item.demand):
                continue
            self._hold(item.demand)
            phase, minutes = self._duration(item, sampler)
            self.treatments.append(
                Treatment(
                    id=item.id, severity=item.severity, held=dict(item.demand), phase=phase,
                    end_tick=tick + minutes, needs_or=item.needs_or, background=item.background,
                )
            )
            self.remove_from_queue(item.id)
            if not item.background:
                admitted.append(item.id)
        return admitted

    def finish_treatments(self, tick: int, sampler: Sampler) -> list[str]:
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
                    t.end_tick = tick + sampler.minutes(sampler.cfg.operating_room)
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
        self, tick: int, sampler: Sampler, *, in_treatment: bool, remaining: int | None = None
    ) -> None:
        self.background_seq += 1
        item = QueueItem(
            id=f"BG-{self.id}-{self.background_seq}",
            severity=Severity.MINOR,
            demand={"er_bed": 1, "trauma_bay": 0, "or": 0, "surgeon": 0, "nurse_slot": 1},
            arrival_tick=tick,
            background=True,
        )
        if in_treatment:
            self._hold(item.demand)
            end = tick + (remaining if remaining is not None else sampler.minutes(
                sampler.cfg.er_background))
            self.treatments.append(
                Treatment(id=item.id, severity=item.severity, held=dict(item.demand), phase="er",
                          end_tick=end, background=True)
            )
        else:
            self.enqueue(item)

    # --- staff loans --------------------------------------------------------------------------

    def can_lend(self, n: int) -> bool:
        """R8: the lender stays at or above `min_nurse_coverage` and strands no current patient."""
        after = self.effective_nurses - n
        return (
            n > 0
            and after >= self.config.min_nurse_coverage
            and self.free("nurse_slot") >= n * PATIENTS_PER_NURSE
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
