from simulation_engine.simulator import Simulator


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
