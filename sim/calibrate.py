"""Calibrate timing from San Francisco Fire Department / EMS calls-for-service data (PLAN §9).

    python -m sim.calibrate data/raw/sf_calls.csv

The owner downloads a sample of the public "Fire Department and Emergency Medical Services
Dispatched Calls for Service" dataset (DataSF) into `data/raw/`. This writes
`data/calibration.json` with quantiles (p25, median, p75, p90, in minutes) for:

- travel: dispatch -> on scene (first medical unit per call)
- scene: on scene -> transport (transporting medical unit per call)
- turnaround: hospital arrival -> unit available (a proxy for offload + cleanup)

Cleaning: medical units only (unit type MEDIC or PRIVATE), intervals kept between 0.1 and
120 minutes, one unit per call. If the file is absent the simulator uses its defaults.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from config.settings import DATA_DIR

MEDICAL_UNITS = {"MEDIC", "PRIVATE"}
MIN_MINUTES, MAX_MINUTES = 0.1, 120.0
COLUMNS = {
    "call": "Call Number", "unit_type": "Unit Type", "dispatch": "Dispatch DtTm",
    "on_scene": "On Scene DtTm", "transport": "Transport DtTm", "hospital": "Hospital DtTm",
    "available": "Available DtTm",
}
CALIBRATION_PATH = DATA_DIR / "calibration.json"


def _minutes(end: pd.Series, start: pd.Series) -> pd.Series:
    return (end - start).dt.total_seconds() / 60.0


def _clean(s: pd.Series) -> pd.Series:
    s = s.dropna()
    return s[(s >= MIN_MINUTES) & (s <= MAX_MINUTES)]


def _quantiles(s: pd.Series) -> dict[str, float]:
    return {"n": int(s.size), "p25": round(float(s.quantile(0.25)), 1),
            "median": round(float(s.quantile(0.5)), 1), "p75": round(float(s.quantile(0.75)), 1),
            "p90": round(float(s.quantile(0.9)), 1)}


def calibrate(csv_path: str | Path) -> dict:
    raw = pd.read_csv(csv_path, dtype=str)
    missing = [c for c in COLUMNS.values() if c not in raw.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    df = raw[[*COLUMNS.values()]].rename(columns={v: k for k, v in COLUMNS.items()})
    df = df[df["unit_type"].str.upper().isin(MEDICAL_UNITS)].copy()
    for col in ("dispatch", "on_scene", "transport", "hospital", "available"):
        df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
    df["travel"] = _minutes(df["on_scene"], df["dispatch"])
    df["scene"] = _minutes(df["transport"], df["on_scene"])
    df["turnaround"] = _minutes(df["available"], df["hospital"])

    first_on_scene = df.dropna(subset=["on_scene"]).sort_values("on_scene") \
        .drop_duplicates("call")
    transporting = df.dropna(subset=["transport"]).sort_values("transport") \
        .drop_duplicates("call")
    return {
        "source": str(Path(csv_path).name),
        "rows": int(len(raw)),
        "medical_rows": int(len(df)),
        "calls": int(df["call"].nunique()),
        "intervals": {
            "travel": _quantiles(_clean(first_on_scene["travel"])),
            "scene": _quantiles(_clean(transporting["scene"])),
            "turnaround": _quantiles(_clean(transporting["turnaround"])),
        },
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Calibrate ORCA-EMS timing from SF EMS data.")
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path, default=CALIBRATION_PATH)
    args = ap.parse_args(argv)
    result = calibrate(args.csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}: {json.dumps(result['intervals'])}")


if __name__ == "__main__":
    main()
