import unittest

from world_model.simulation_engine import Scenario, SimulationEngine


class TestScenario(unittest.TestCase):
    def test_defaults(self):
        s = Scenario(id="s1", initial_state={}, actions=[])
        self.assertEqual(s.id, "s1")
        self.assertEqual(s.probability, 1.0)
        self.assertEqual(s.outcomes, {})


class TestSimulationEngine(unittest.TestCase):
    def test_generate_scenarios(self):
        engine = SimulationEngine(random_seed=42)
        state = {"value": 0.0}
        scenarios = engine.generate_scenarios(state, n=3)
        self.assertEqual(len(scenarios), 3)
        self.assertEqual(scenarios[0].id, "scenario_0")

    def test_generate_scenarios_reproducible(self):
        engine = SimulationEngine(random_seed=0)
        state = {"value": 0.0}
        scenarios_a = engine.generate_scenarios(state, n=5)
        engine_b = SimulationEngine(random_seed=0)
        scenarios_b = engine_b.generate_scenarios(state, n=5)
        actions_a = [a["magnitude"] for s in scenarios_a for a in s.actions]
        actions_b = [a["magnitude"] for s in scenarios_b for a in s.actions]
        self.assertEqual(actions_a, actions_b)

    def test_run_monte_carlo(self):
        engine = SimulationEngine(random_seed=0)
        state = {"value": 0.0}
        result = engine.run_monte_carlo(state, horizon=3, samples=20)
        self.assertIn("mean", result)
        self.assertIn("std", result)
        self.assertIn("min", result)
        self.assertIn("max", result)
        self.assertEqual(result["samples"], 20)

    def test_evaluate_scenario(self):
        engine = SimulationEngine()
        s = Scenario(id="s1", initial_state={}, actions=[{"type": "interact", "magnitude": 0.5}])
        outcome = engine.evaluate_scenario(s)
        self.assertIn("value", outcome)

    def test_top_scenarios_empty(self):
        engine = SimulationEngine()
        self.assertEqual(engine.top_scenarios(), [])

    def test_top_scenarios_ranked(self):
        engine = SimulationEngine()
        engine.scenarios = [
            Scenario(id="low", initial_state={}, actions=[{"type": "wait", "magnitude": 0.1}]),
            Scenario(id="high", initial_state={}, actions=[{"type": "interact", "magnitude": 1.0}]),
        ]
        engine.scenarios[0].outcomes = {"value": 0.0}
        engine.scenarios[1].outcomes = {"value": 5.0}
        top = engine.top_scenarios(n=1)
        self.assertEqual(top[0].id, "high")


if __name__ == "__main__":
    unittest.main()
