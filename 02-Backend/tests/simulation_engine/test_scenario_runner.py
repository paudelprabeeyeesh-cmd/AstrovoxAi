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
