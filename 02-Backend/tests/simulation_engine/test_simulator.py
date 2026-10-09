from simulation_engine.simulator import Simulator, SimulationState


def test_simulator_step_affects_value():
    sim = Simulator(seed=1)
    result = sim.simulate_step({"value": 0.0}, [{"type": "interact", "magnitude": 0.8}])
    assert result["value"] == 0.8


def test_simulator_step_wait_reduces_value():
    sim = Simulator(seed=1)
    result = sim.simulate_step({"value": 1.0}, [{"type": "wait", "magnitude": 0.5}])
    assert result["value"] == 0.95


def test_run_trajectory_horizon():
    sim = Simulator(seed=1)
    traj = sim.run_trajectory({"value": 0.0}, [{"type": "interact", "magnitude": 1.0}], horizon=3)
    assert len(traj) == 4
    assert traj[-1]["value"] == 3.0


def test_compute_outcome():
    sim = Simulator(seed=1)
    outcome = sim.compute_outcome({"value": 2.5})
    assert outcome == {"value": 2.5}


def test_run_monte_carlo_returns_list():
    sim = Simulator(seed=1)
    results = sim.run_monte_carlo({"value": 0.0}, samples=5, horizon=2)
    assert len(results) == 5
    assert all(isinstance(v, float) for v in results)


def test_simulation_state_dataclass():
    state = SimulationState(state={"value": 1.0})
    assert state.state == {"value": 1.0}


def test_simulate_step_unknown_action_type():
    sim = Simulator(seed=1)
    result = sim.simulate_step({"value": 1.0}, [{"type": "unknown", "magnitude": 0.5}])
    assert result["value"] == 0.975


def test_simulate_step_preserves_original_state():
    sim = Simulator(seed=1)
    original = {"value": 1.0}
    result = sim.simulate_step(original, [{"type": "interact", "magnitude": 0.5}])
    assert original == {"value": 1.0}
    assert result == {"value": 1.5}


def test_run_trajectory_no_actions():
    sim = Simulator(seed=1)
    traj = sim.run_trajectory({"value": 1.0}, [], horizon=3)
    assert len(traj) == 4
    assert all(step == {"value": 1.0} for step in traj)


def test_compute_outcome_missing_value():
    sim = Simulator(seed=1)
    outcome = sim.compute_outcome({})
    assert outcome == {"value": 0.0}


def test_simulator_stores_seed():
    sim = Simulator(seed=42)
    assert sim.seed == 42


def test_run_monte_carlo_empty_state():
    sim = Simulator(seed=1)
    results = sim.run_monte_carlo({}, samples=3, horizon=1)
    assert len(results) == 3
    assert all(v == 0.0 for v in results)
