import json

from sim.engine import Engine
from sim.generator import generate
from sim.observations import Observation, ObsPatient
from tests.helpers import GreedyTestPolicy


class Recorder(GreedyTestPolicy):
    """Nearest-style policy that keeps every observation it is given."""

    def __init__(self):
        super().__init__()
        self.seen: list[Observation] = []

    def decide(self, obs):
        self.seen.append(obs.model_copy(deep=True))
        return super().decide(obs)


def run(info, until=150):
    policy = Recorder()
    engine = Engine(generate(7, "surge"), policy, info=info)
    snapshots = {}

    def hook(e):
        snapshots[e.tick] = {h: {"er_bed": hs.free("er_bed"), "ward_bed": hs.free("ward_bed")}
                             for h, hs in e.hospitals.items()}

    engine.tick_hook = hook
    engine.run(until=until)
    return engine, policy, snapshots


def test_partial_board_is_stale_between_updates_and_differs_from_truth():
    _, policy, truth = run("partial")
    differs = 0
    for obs in policy.seen:
        assert obs.hospitals["A"].board_tick == obs.tick - obs.tick % 15
        live = truth.get(obs.tick - 1)
        if live and any(obs.hospitals[h].free["er_bed"] != live[h]["er_bed"] for h in live):
            differs += 1
    assert differs > 0  # the board lags reality between 15-minute updates


def test_complete_board_is_live():
    _, policy, _ = run("complete", until=60)
    assert all(o.hospitals["A"].board_tick == o.tick for o in policy.seen)


def test_partial_hides_victims_until_scene_report():
    engine, policy, _ = run("partial")
    call = engine.incidents["MCI-2"].call_tick
    first = next(o for o in policy.seen if "MCI-2" in o.incidents)
    assert first.tick == call and first.incidents["MCI-2"].patients == []
    assert first.incidents["MCI-2"].reported_victims == engine.incidents["MCI-2"].reported_victims
    later = next(o for o in policy.seen if "MCI-2" in o.incidents
                 and o.incidents["MCI-2"].scene_reported)
    assert later.incidents["MCI-2"].patients
    assert all(p.severity is not None for p in later.incidents["MCI-2"].patients)


def test_complete_shows_true_severity_after_call():
    engine, policy, _ = run("complete", until=40)
    obs = next(o for o in policy.seen if "MCI-2" in o.incidents)
    for p in obs.incidents["MCI-2"].patients:
        assert p.severity == engine.patients[p.id].true_severity


def test_observations_never_contain_hidden_fields():
    assert "true_severity" not in ObsPatient.model_fields
    _, policy, _ = run("partial", until=60)
    text = json.dumps([o.model_dump(mode="json", exclude={"timing"}) for o in policy.seen])
    for hidden in ("true_severity", "true_victim_ids", "secure_delay_min", "extrication_min",
                   "deterioration_rate", "survival_prob"):
        assert hidden not in text


def test_rejections_come_back_as_codes_only():
    _, policy, _ = run("complete", until=200)
    rejections = [r for o in policy.seen for r in o.rejections]
    assert rejections, "the surge should produce at least one validator rejection"
    assert all(set(r.model_dump()) == {"tick", "action", "rule_id", "code"} for r in rejections)
