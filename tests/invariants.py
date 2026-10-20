"""Engine invariants (PLAN §19). Call `check_invariants(engine)` after every tick."""

from __future__ import annotations

from collections import Counter

from sim.engine import Engine
from sim.entities import AmbulanceState, PatientStatus
from sim.hospital import RESOURCES


class InvariantViolation(AssertionError):
    pass


def check_invariants(engine: Engine) -> None:
    errors: list[str] = []
    A = AmbulanceState

    # 1. No unit double-booked / no patient assigned to two units.
    assigned = Counter(pid for a in engine.ambulances.values() for pid in a.assigned_patient_ids)
    errors += [f"patient {pid} assigned to {n} units" for pid, n in assigned.items() if n > 1]
    for amb in engine.ambulances.values():
        for pid in amb.assigned_patient_ids:
            if engine.patients[pid].ambulance_id != amb.id:
                errors.append(f"{pid} in {amb.id}.assigned but ambulance_id mismatch")
        if amb.state == A.IDLE and (amb.assigned_incident or amb.assigned_patient_ids):
            errors.append(f"{amb.id} IDLE but still assigned")

    # 2. Resource counts within [0, capacity].
    for hs in engine.hospitals.values():
        for r in RESOURCES:
            occ, tot = hs.occupied[r], hs.total(r)
            if not 0 <= occ <= tot:
                errors.append(f"hospital {hs.id} {r} occupied={occ} total={tot}")
        if hs.effective_nurses < 0:
            errors.append(f"hospital {hs.id} negative nurses")
        held = Counter()
        for t in hs.treatments:
            held.update(t.held)
        for r in RESOURCES:
            if held[r] != hs.occupied[r]:
                errors.append(f"hospital {hs.id} {r} held={held[r]} occupied={hs.occupied[r]}")

    # 3. No patient in two places; status consistent with location.
    places: Counter[str] = Counter()
    queued: set[str] = set()
    treated: set[str] = set()
    for hs in engine.hospitals.values():
        for q in hs.queue:
            if not q.background:
                places[q.id] += 1
                queued.add(q.id)
        for t in hs.treatments:
            if not t.background:
                places[t.id] += 1
                treated.add(t.id)
    onboard = {pid for a in engine.ambulances.values() if a.state == A.TRANSPORTING
               for pid in a.onboard_patient_ids}
    for pid in onboard:
        places[pid] += 1
    for pid, n in places.items():
        if n > 1:
            errors.append(f"patient {pid} in {n} places")
    for p in engine.patients.values():
        if p.status == PatientStatus.WAITING_AT_ER and p.id not in queued:
            errors.append(f"{p.id} WAITING_AT_ER but not queued")
        if p.status == PatientStatus.IN_TREATMENT and p.id not in treated:
            errors.append(f"{p.id} IN_TREATMENT but not in a treatment")
        if p.status == PatientStatus.IN_TRANSPORT and p.id not in onboard:
            errors.append(f"{p.id} IN_TRANSPORT but not onboard a transporting unit")

    # 4. No unit inside an unsecured violent scene.
    for amb in engine.ambulances.values():
        if amb.state in (A.ON_SCENE, A.LOADING) and amb.assigned_incident:
            inc = engine.incidents[amb.assigned_incident]
            if inc.violent and not inc.scene_secured:
                errors.append(f"{amb.id} {amb.state} at unsecured scene {inc.id}")

    # 5. Every committed action passed the validator.
    for c in engine.commits:
        if c["committed"] and not all(r["ok"] for r in c["results"]):
            errors.append(f"committed action failed validation: {c}")

    if errors:
        raise InvariantViolation(f"tick {engine.tick}: " + "; ".join(errors))
