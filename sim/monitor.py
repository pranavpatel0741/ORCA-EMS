"""Deterministic threshold alerts (PLAN §15 M4). Not an LLM.

Each alert is logged as a MONITOR_ALERT event when its condition starts ("RAISED") and when it
ends ("CLEARED"), so the log stays small and the dashboard can show what is currently active.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sim.entities import AmbulanceState, IncidentType, PatientStatus
from sim.events import EventType

if TYPE_CHECKING:
    from sim.engine import Engine

ER_FULL = 0.90
ER_WAIT_MIN = 20
SURGE_WAITING = 5
MCI_TYPES = {IncidentType.BUS_CRASH, IncidentType.SHOOTING}


def district(engine: Engine, loc: tuple[float, float]) -> str:
    """Quadrant of the town (NW / NE / SW / SE) from a location."""
    lats = [h.config.location[0] for h in engine.hospitals.values()]
    lons = [h.config.location[1] for h in engine.hospitals.values()]
    mid_lat = (min(lats) + max(lats)) / 2
    mid_lon = (min(lons) + max(lons)) / 2
    return ("N" if loc[0] >= mid_lat else "S") + ("E" if loc[1] >= mid_lon else "W")


class Monitor:
    def __init__(self) -> None:
        self.active: dict[tuple[str, str], str] = {}  # (alert, key) -> message

    def conditions(self, engine: Engine) -> dict[tuple[str, str], str]:
        out: dict[tuple[str, str], str] = {}
        for hid, hs in sorted(engine.hospitals.items()):
            occ = hs.er_occupancy()
            if occ >= ER_FULL:
                out[("HOSPITAL_FULL", hid)] = f"Hospital {hid} ER at {occ:.0%} of capacity"
            waits = [engine.tick - q.arrival_tick for q in hs.queue if not q.background]
            if waits and max(waits) > ER_WAIT_MIN:
                out[("ER_WAIT", hid)] = (f"Hospital {hid}: a patient has waited {max(waits)} min "
                                         "for a bed")
        homes: dict[str, list] = {}
        for amb in engine.ambulances.values():
            if engine.unit_available(amb.id):
                homes.setdefault(district(engine, amb.home_station), []).append(amb)
        for d, units in sorted(homes.items()):
            if not any(a.state == AmbulanceState.IDLE for a in units):
                out[("NO_FREE_UNITS", d)] = f"No free ambulance in the {d} district"
        waiting = sum(1 for p in engine.patients.values()
                      if p.status == PatientStatus.WAITING_ON_SCENE
                      and p.incident_id in engine.active_incidents)
        mci = [i.id for i in engine.active_incidents.values() if i.type in MCI_TYPES]
        if mci or waiting >= SURGE_WAITING:
            what = ", ".join(mci) if mci else f"{waiting} patients waiting on scene"
            out[("SURGE", "town")] = f"Surge detected: {what}"
        return out

    def update(self, engine: Engine) -> None:
        now = self.conditions(engine)
        for key in sorted(set(now) - set(self.active)):
            engine.log.emit(engine.tick, EventType.MONITOR_ALERT, "monitor",
                            {"alert": key[0], "key": key[1], "phase": "RAISED",
                             "message": now[key]})
        for key in sorted(set(self.active) - set(now)):
            engine.log.emit(engine.tick, EventType.MONITOR_ALERT, "monitor",
                            {"alert": key[0], "key": key[1], "phase": "CLEARED",
                             "message": f"Cleared: {self.active[key]}"})
        self.active = now
