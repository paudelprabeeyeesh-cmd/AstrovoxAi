from simulation_engine.replay_controller import ReplayController
from simulation_engine.simulator import Simulator


def test_record_and_replay():
    rc = ReplayController(seed=1)
    rc.record("scenario_1", {"value": 0.0}, [{"type": "interact", "magnitude": 0.9}])
    assert len(rc.get_records()) == 1
    results = rc.replay(Simulator)
    assert results[0]["value"] == 0.9


def test_replay_is_deterministic():
    rc1 = ReplayController(seed=1)
    rc1.record("s", {"value": 0.0}, [{"type": "interact", "magnitude": 0.9}])
    rc2 = ReplayController(seed=1)
    rc2.record("s", {"value": 0.0}, [{"type": "interact", "magnitude": 0.9}])
    assert rc1.replay(Simulator) == rc2.replay(Simulator)


def test_replay_controller_get_records_returns_copy():
    rc = ReplayController(seed=1)
    rc.record("s", {"value": 0.0}, [{"type": "interact", "magnitude": 0.9}])
    recs = rc.get_records()
    recs.clear()
    assert len(rc.get_records()) == 1
