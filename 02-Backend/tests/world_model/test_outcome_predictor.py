import unittest

from world_model.outcome_predictor import OutcomePredictor


class TestOutcomePredictor(unittest.TestCase):
    def test_init(self):
        predictor = OutcomePredictor(window=5)
        self.assertEqual(predictor.window, 5)
        self.assertEqual(predictor.history, [])

    def test_add_observation(self):
        predictor = OutcomePredictor()
        predictor.add_observation(1.0)
        self.assertEqual(predictor.history, [1.0])

    def test_predict_empty_history(self):
        predictor = OutcomePredictor()
        means, stds = predictor.predict(horizon=3)
        self.assertEqual(means, [0.0, 0.0, 0.0])
        self.assertEqual(stds, [1.0, 1.0, 1.0])

    def test_predict_single_value(self):
        predictor = OutcomePredictor()
        predictor.add_observation(5.0)
        means, stds = predictor.predict(horizon=2)
        self.assertEqual(means, [5.0, 5.0])

    def test_predict_multiple_values(self):
        predictor = OutcomePredictor(window=3)
        for v in [1.0, 2.0, 3.0, 4.0]:
            predictor.add_observation(v)
        means, stds = predictor.predict(horizon=2)
        expected_mean = (2.0 + 3.0 + 4.0) / 3
        self.assertAlmostEqual(means[0], expected_mean)
        self.assertGreaterEqual(stds[0], 0.0)

    def test_confidence_empty(self):
        predictor = OutcomePredictor()
        self.assertEqual(predictor.confidence(), 0.0)

    def test_confidence_range(self):
        predictor = OutcomePredictor()
        predictor.add_observation(1.0)
        predictor.add_observation(2.0)
        conf = predictor.confidence()
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)


if __name__ == "__main__":
    unittest.main()
