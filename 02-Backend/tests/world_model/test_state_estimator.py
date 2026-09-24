import unittest

from world_model.state_estimator import StateEstimate, StateEstimator


class TestStateEstimator(unittest.TestCase):
    def test_init(self):
        estimator = StateEstimator(state_dim=4)
        self.assertEqual(estimator.state_dim, 4)
        self.assertEqual(len(estimator.estimate.state), 4)

    def test_update(self):
        estimator = StateEstimator(state_dim=2)
        estimate = estimator.update([1.0, 1.0])
        self.assertIsInstance(estimate, StateEstimate)
        self.assertEqual(len(estimate.state), 2)

    def test_update_wrong_dimension(self):
        estimator = StateEstimator(state_dim=2)
        with self.assertRaises(ValueError):
            estimator.update([1.0])

    def test_predict(self):
        estimator = StateEstimator(state_dim=2)
        estimator.update([1.0, 1.0])
        predictions = estimator.predict(steps=3)
        self.assertEqual(len(predictions), 3)
        for pred in predictions:
            self.assertIsInstance(pred, StateEstimate)

    def test_uncertainty_initial(self):
        estimator = StateEstimator(state_dim=2)
        self.assertEqual(estimator.uncertainty(), 1.0)

    def test_confidence(self):
        estimator = StateEstimator(state_dim=2)
        conf = estimator.confidence()
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)


if __name__ == "__main__":
    unittest.main()
