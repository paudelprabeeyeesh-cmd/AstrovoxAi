import unittest

from world_model.counterfactual_generator import Counterfactual, CounterfactualGenerator


class TestCounterfactualGenerator(unittest.TestCase):
    def test_generate(self):
        gen = CounterfactualGenerator()
        factual = {"x": 1, "y": 2, "z": 3}
        intervention = {"x": 10}
        cf = gen.generate(factual, intervention, "z")
        self.assertIsInstance(cf, Counterfactual)
        self.assertEqual(cf.intervention, {"x": 10})
        self.assertEqual(cf.outcome, {"z": 3})

    def test_generate_changes_outcome(self):
        gen = CounterfactualGenerator()
        factual = {"reward": 0, "action": "go"}
        intervention = {"action": "stop"}
        cf = gen.generate(factual, intervention, "reward")
        self.assertEqual(cf.intervention, {"action": "stop"})

    def test_difference_numeric(self):
        gen = CounterfactualGenerator()
        factual = {"a": 1, "b": 2}
        counterfactual = {"a": 5, "b": 2}
        diffs = gen.difference(factual, counterfactual)
        self.assertEqual(diffs["a"], 4.0)
        self.assertNotIn("b", diffs)

    def test_difference_mixed(self):
        gen = CounterfactualGenerator()
        factual = {"x": 1}
        counterfactual = {"x": 2, "y": "hello"}
        diffs = gen.difference(factual, counterfactual)
        self.assertEqual(diffs["x"], 1.0)
        self.assertNotIn("y", diffs)

    def test_probability(self):
        gen = CounterfactualGenerator()
        cf = Counterfactual(intervention={"a": 1}, outcome={"a": 1}, probability=0.8)
        self.assertEqual(gen.probability(cf), 0.8)

    def test_best_explanation(self):
        gen = CounterfactualGenerator()
        scenarios = [
            Counterfactual(intervention={"a": 1}, outcome={"a": 1}, probability=0.3),
            Counterfactual(intervention={"a": 2}, outcome={"a": 2}, probability=0.9),
        ]
        best = gen.best_explanation(scenarios)
        self.assertEqual(best.probability, 0.9)

    def test_best_explanation_empty(self):
        gen = CounterfactualGenerator()
        with self.assertRaises(ValueError):
            gen.best_explanation([])


if __name__ == "__main__":
    unittest.main()
