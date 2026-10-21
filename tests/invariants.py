"""Engine invariants (PLAN §19). Call `check_invariants(engine)` after every tick."""

from __future__ import annotations

from collections import Counter

from sim.engine import Engine
from sim.entities import AmbulanceState, PatientStatus, Severity
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

    # 5. Every committed action passed the validator, and current state matches validated
    #    decisions: a transporting unit carries only patients validated for its destination.
    for c in engine.commits:
        if c["committed"] and not all(r["ok"] for r in c["results"]):
            errors.append(f"committed action failed validation: {c}")
    for amb in engine.ambulances.values():
        if amb.state != A.TRANSPORTING:
            continue
        validated = engine.validated_dest.get(amb.id)
        if validated is None or validated[1] != amb.destination_hospital \
                or not set(amb.onboard_patient_ids) <= validated[0]:
            errors.append(f"{amb.id} transporting {amb.onboard_patient_ids} to "
                          f"{amb.destination_hospital} without a matching validated decision")

    # 6. Destination can structurally receive onboard patients; R7 holds onboard.
    for amb in engine.ambulances.values():
        if amb.state != A.TRANSPORTING:
            continue
        hs = engine.hospitals[amb.destination_hospital]
        onboard = [engine.patients[p] for p in amb.onboard_patient_ids]
        for p in onboard:
            if not hs.has_resource_types(engine.demand_at(hs.id, p)):
                errors.append(f"{amb.id} carries {p.id} to {hs.id} lacking resource types")
        n_crit = sum(1 for p in onboard if p.true_severity == Severity.CRITICAL)
        if len(onboard) > 2 or (n_crit and len(onboard) > 1):
            errors.append(f"{amb.id} onboard violates R7: {amb.onboard_patient_ids}")

    # 7. Patient timestamps never go backward.
    for p in engine.patients.values():
        ts = p.timestamps
        seq = [ts.call, ts.loaded, ts.arrived_hospital, ts.definitive_care_start, ts.discharged]
        seq = [t for t in seq if t is not None]
        if seq != sorted(seq) or (ts.unit_on_scene is not None and ts.unit_on_scene < ts.call):
            errors.append(f"{p.id} timestamps out of order: {ts}")

    # 8. A unit is moving exactly when it has a route.
    for amb in engine.ambulances.values():
        moving = amb.state in (A.EN_ROUTE, A.TRANSPORTING, A.RETURNING)
        if moving != (amb.id in engine.legs):
            errors.append(f"{amb.id} state {amb.state} but route={amb.id in engine.legs}")

    if errors:
        raise InvariantViolation(f"tick {engine.tick}: " + "; ".join(errors))
