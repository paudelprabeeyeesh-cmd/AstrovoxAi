from simulation_engine.replay_controller import ReplayController, ReplayRecord
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


def test_replay_record_dataclass():
    rec = ReplayRecord(
        scenario_id="s1",
        initial_state={"value": 0.0},
        actions=[{"type": "interact"}],
        seed=1,
        timestamp=100.0,
    )
    assert rec.scenario_id == "s1"
    assert rec.initial_state == {"value": 0.0}
    assert rec.actions == [{"type": "interact"}]
    assert rec.seed == 1
    assert rec.timestamp == 100.0


def test_record_stores_deep_copy():
    rc = ReplayController(seed=1)
    state = {"value": 0.0}
    actions = [{"type": "interact", "magnitude": 0.9}]
    rc.record("s", state, actions)
    state["value"] = 1.0
    actions[0]["magnitude"] = 0.5
    rec = rc.get_records()[0]
    assert rec.initial_state == {"value": 0.0}
    assert rec.actions == [{"type": "interact", "magnitude": 0.9}]


def test_replay_multiple_records():
    rc = ReplayController(seed=1)
    rc.record("s1", {"value": 0.0}, [{"type": "interact", "magnitude": 1.0}])
    rc.record("s2", {"value": 0.0}, [{"type": "interact", "magnitude": 2.0}])
    results = rc.replay(Simulator)
    assert len(results) == 2
    assert results[0]["value"] == 1.0
    assert results[1]["value"] == 2.0


def test_replay_with_different_seeds():
    rc1 = ReplayController(seed=1)
    rc1.record("s", {"value": 0.0}, [{"type": "interact", "magnitude": 1.0}])
    rc2 = ReplayController(seed=2)
    rc2.record("s", {"value": 0.0}, [{"type": "interact", "magnitude": 1.0}])
    results1 = rc1.replay(Simulator)
    results2 = rc2.replay(Simulator)
    assert results1 == results2


def test_replay_controller_empty_records():
    rc = ReplayController(seed=1)
    results = rc.replay(Simulator)
    assert results == []
