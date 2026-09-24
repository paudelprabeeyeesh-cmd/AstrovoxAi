import pytest
import numpy as np
from world_model.simulation_engine import SimulationEngine, Scenario


class TestSimulationEngine:
    def test_generate_scenarios(self):
        engine = SimulationEngine(random_seed=42)
        scenarios = engine.generate_scenarios({"value": 0.0}, n=5)
        assert len(scenarios) == 5
        assert all(s.initial_state["value"] == 0.0 for s in scenarios)

    def test_run_monte_carlo(self):
        engine = SimulationEngine(random_seed=42)
        result = engine.run_monte_carlo({"value": 0.0}, horizon=3, samples=50)
        assert "mean" in result
        assert "std" in result
        assert result["samples"] == 50
        assert isinstance(result["mean"], float)

    def test_evaluate_scenario(self):
        engine = SimulationEngine(random_seed=42)
        scenario = Scenario(id="s1", initial_state={"value": 0.0}, actions=[{"type": "interact", "magnitude": 0.8}])
        outcomes = engine.evaluate_scenario(scenario)
        assert "value" in outcomes
        assert outcomes["value"] > 0.0

    def test_top_scenarios(self):
        engine = SimulationEngine(random_seed=42)
        engine.generate_scenarios({"value": 0.0}, n=3)
        for s in engine.scenarios:
            engine.evaluate_scenario(s)
        top = engine.top_scenarios(n=2)
        assert len(top) == 2

    def test_monte_carlo_deterministic_with_seed(self):
        engine = SimulationEngine(random_seed=7)
        r1 = engine.run_monte_carlo({"value": 1.0}, horizon=2, samples=10)
        engine2 = SimulationEngine(random_seed=7)
        r2 = engine2.run_monte_carlo({"value": 1.0}, horizon=2, samples=10)
        assert r1["mean"] == pytest.approx(r2["mean"])
