import json
from pathlib import Path

from sim.calibrate import calibrate, main
from sim.travel import TimingConfig, load_timing

FIXTURE = Path(__file__).parent / "fixtures" / "sf_ems_sample.csv"


def test_calibrate_on_fixture_cleans_and_dedupes():
    result = calibrate(FIXTURE)
    assert result["rows"] == 10 and result["medical_rows"] == 9  # engine row dropped
    travel = result["intervals"]["travel"]
    # C1 counts once (first medic on scene, 8 min); C5 (0 min) and C6 (400 min) are dropped.
    assert travel["n"] == 6
    assert travel["median"] == 9.0  # 7, 8, 9, 9, 11, 12
    scene = result["intervals"]["scene"]
    assert scene["n"] == 6 and 12 <= scene["median"] <= 19


def test_load_timing_uses_calibration_file(tmp_path):
    out = tmp_path / "calibration.json"
    main([str(FIXTURE), "--out", str(out)])
    data = json.loads(out.read_text())
    cfg = load_timing(out)
    assert cfg.scene_time_other == (round(data["intervals"]["scene"]["p25"]),
                                    round(data["intervals"]["scene"]["p75"]))
    assert cfg.handover[0] >= 1 and cfg.handover[1] >= cfg.handover[0]


def test_load_timing_defaults_without_file(tmp_path):
    assert load_timing(tmp_path / "missing.json") == TimingConfig()
