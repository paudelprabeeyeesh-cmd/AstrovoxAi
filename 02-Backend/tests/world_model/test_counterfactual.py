import unittest

from world_model.counterfactual import CounterfactualEngine, CounterfactualScenario


class TestCounterfactualScenario(unittest.TestCase):
    def test_defaults(self):
        s = CounterfactualScenario(intervention={"a": 1}, outcome={"a": 1})
        self.assertEqual(s.intervention, {"a": 1})
        self.assertEqual(s.probability, 1.0)
        self.assertEqual(s.description, "")

    def test_custom_values(self):
        s = CounterfactualScenario(intervention={}, outcome={}, probability=0.8, description="desc")
        self.assertEqual(s.probability, 0.8)
        self.assertEqual(s.description, "desc")


class TestCounterfactualEngine(unittest.TestCase):
    def test_generate(self):
        engine = CounterfactualEngine()
        factual = {"a": 1, "b": 2}
        intervention = {"a": 10}
        scenario = engine.generate(factual, intervention, "b")
        self.assertIsInstance(scenario, CounterfactualScenario)
        self.assertEqual(scenario.intervention, intervention)
        self.assertEqual(scenario.outcome, {"b": 2})

    def test_generate_counterfactual_outcome(self):
        engine = CounterfactualEngine()
        factual = {"reward": 0}
        intervention = {"reward": 5}
        scenario = engine.generate(factual, intervention, "reward")
        self.assertEqual(scenario.outcome["reward"], 5)

    def test_difference_numeric(self):
        engine = CounterfactualEngine()
        diffs = engine.difference({"a": 1, "b": 2}, {"a": 5, "b": 7})
        self.assertEqual(diffs["a"], 4.0)
        self.assertEqual(diffs["b"], 5.0)

    def test_difference_non_numeric(self):
        engine = CounterfactualEngine()
        diffs = engine.difference({"a": "x"}, {"a": "y"})
        self.assertEqual(diffs, {})

    def test_difference_union(self):
        engine = CounterfactualEngine()
        diffs = engine.difference({"a": 1}, {"a": 2, "b": 3})
        self.assertEqual(diffs["a"], 1.0)
        self.assertEqual(diffs["b"], 3.0)

    def test_probability(self):
        engine = CounterfactualEngine()
        s = CounterfactualScenario(intervention={}, outcome={}, probability=0.5)
        self.assertEqual(engine.probability(s), 0.5)

    def test_best_explanation(self):
        engine = CounterfactualEngine()
        scenarios = [
            CounterfactualScenario(intervention={}, outcome={}, probability=0.3),
            CounterfactualScenario(intervention={}, outcome={}, probability=0.9),
        ]
        best = engine.best_explanation(scenarios)
        self.assertEqual(best.probability, 0.9)

    def test_best_explanation_empty(self):
        engine = CounterfactualEngine()
        with self.assertRaises(ValueError):
            engine.best_explanation([])

    def test_compare_scenarios(self):
        engine = CounterfactualEngine()
        a = CounterfactualScenario(intervention={"x": 1}, outcome={})
        b = CounterfactualScenario(intervention={"x": 3}, outcome={})
        diff = engine.compare_scenarios(a, b)
        self.assertEqual(diff["x"], 2.0)


if __name__ == "__main__":
    unittest.main()
