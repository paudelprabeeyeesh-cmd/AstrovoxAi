from simulation_engine.scenario_runner import Scenario, ScenarioRunner


def test_run_scenario_returns_final_state():
    runner = ScenarioRunner(seed=1)
    s = Scenario(id="s1", initial_state={"value": 0.0}, actions=[{"type": "interact", "magnitude": 0.7}])
    final = runner.run_scenario(s, horizon=2)
    assert final["value"] == 1.4


def test_run_scenario_trajectory_length():
    runner = ScenarioRunner(seed=1)
    s = Scenario(id="s1", initial_state={"value": 0.0}, actions=[{"type": "interact", "magnitude": 1.0}])
    traj = runner.run_scenario_trajectory(s, horizon=3)
    assert len(traj) == 4
    assert traj[-1]["value"] == 3.0


def test_execute_actions_returns_copy():
    runner = ScenarioRunner(seed=1)
    state = {"value": 0.0}
    new_state = runner.execute_actions(state, [{"type": "interact", "magnitude": 0.5}])
    assert new_state == {"value": 0.5}
    assert state == {"value": 0.0}


def test_scenario_dataclass():
    s = Scenario(id="s1", initial_state={"value": 0.0}, actions=[{"type": "interact"}])
    assert s.id == "s1"
    assert s.initial_state == {"value": 0.0}
    assert s.actions == [{"type": "interact"}]


def test_run_scenario_horizon_zero():
    runner = ScenarioRunner(seed=1)
    s = Scenario(id="s1", initial_state={"value": 1.0}, actions=[{"type": "interact", "magnitude": 0.5}])
    final = runner.run_scenario(s, horizon=0)
    assert final == {"value": 1.0}


def test_run_scenario_trajectory_horizon_zero():
    runner = ScenarioRunner(seed=1)
    s = Scenario(id="s1", initial_state={"value": 1.0}, actions=[{"type": "interact", "magnitude": 0.5}])
    traj = runner.run_scenario_trajectory(s, horizon=0)
    assert len(traj) == 1
    assert traj[0] == {"value": 1.0}


def test_execute_actions_unknown_type():
    runner = ScenarioRunner(seed=1)
    state = {"value": 1.0}
    new_state = runner.execute_actions(state, [{"type": "unknown", "magnitude": 0.5}])
    assert new_state["value"] == 0.975


def test_multiple_scenarios_independent():
    runner = ScenarioRunner(seed=1)
    s1 = Scenario(id="s1", initial_state={"value": 0.0}, actions=[{"type": "interact", "magnitude": 1.0}])
    s2 = Scenario(id="s2", initial_state={"value": 0.0}, actions=[{"type": "interact", "magnitude": 2.0}])
    final1 = runner.run_scenario(s1, horizon=1)
    final2 = runner.run_scenario(s2, horizon=1)
    assert final1 == {"value": 1.0}
    assert final2 == {"value": 2.0}
