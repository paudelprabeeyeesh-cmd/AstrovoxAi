import unittest

from world_model.counterfactual_reasoning import CounterfactualReasoner, DecisionTree


class TestCounterfactualReasoner(unittest.TestCase):
    def test_record_history(self):
        r = CounterfactualReasoner()
        r.record_history("h1", [{"value": 1.0}])
        self.assertIn("h1", r.histories)
        self.assertEqual(r.histories["h1"][0]["value"], 1.0)

    def test_generate_alternative(self):
        r = CounterfactualReasoner()
        r.record_history("h1", [{"value": 1.0, "action": "go"}])
        alt = r.generate_alternative("h1", {"action": "stop"})
        self.assertEqual(len(alt), 1)
        self.assertEqual(alt[0]["action"], "stop")
        self.assertEqual(alt[0]["value"], 1.0)

    def test_compare(self):
        r = CounterfactualReasoner()
        actual = [{"value": 1.0, "reward": 2.0, "score": 3.0}]
        alternative = [{"value": 5.0, "reward": 5.0, "score": 5.0}]
        diffs = r.compare(actual, alternative)
        self.assertAlmostEqual(diffs["value"], 4.0)
        self.assertAlmostEqual(diffs["reward"], 3.0)
        self.assertAlmostEqual(diffs["score"], 2.0)

    def test_decision_value(self):
        r = CounterfactualReasoner()
        self.assertAlmostEqual(r.decision_value(1.0, 5.0), 4.0)
        self.assertAlmostEqual(r.decision_value(5.0, 1.0), -4.0)

    def test_best_alternative_none(self):
        r = CounterfactualReasoner()
        self.assertIsNone(r.best_alternative())

    def test_best_alternative(self):
        r = CounterfactualReasoner()
        r.alternatives.append({"events": [{"value": 1.0}, {"value": 2.0}]})
        r.alternatives.append({"events": [{"value": 5.0}, {"value": 6.0}]})
        best = r.best_alternative()
        self.assertIsNotNone(best)
        self.assertEqual(best, r.alternatives[1])

    def test_generate_alternative_missing_key(self):
        r = CounterfactualReasoner()
        r.record_history("h1", [{"value": 1.0, "action": "go"}])
        alt = r.generate_alternative("h1", {"value": 9.0})
        self.assertEqual(alt[0]["value"], 9.0)
        self.assertEqual(alt[0]["action"], "go")


if __name__ == "__main__":
    unittest.main()
