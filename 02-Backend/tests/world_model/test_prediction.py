import unittest

import numpy as np

from world_model.prediction import StatePredictor, TimeSeriesForecaster


class TestStatePredictor(unittest.TestCase):
    def test_init(self):
        p = StatePredictor(state_dim=4)
        self.assertEqual(p.state_dim, 4)
        self.assertEqual(p.history, [])

    def test_fit_empty(self):
        p = StatePredictor(state_dim=2)
        p.fit([])
        self.assertEqual(len(p.history), 0)

    def test_fit_single(self):
        p = StatePredictor(state_dim=2)
        p.fit([np.array([1.0, 2.0])])
        self.assertEqual(len(p.history), 1)

    def test_predict_empty_history(self):
        p = StatePredictor(state_dim=2)
        p.fit([np.array([0.0, 0.0])])
        means, vars_ = p.predict(horizon=3)
        self.assertEqual(means.shape, (4, 2))
        self.assertEqual(vars_.shape, (4,))

    def test_predict_after_fit(self):
        p = StatePredictor(state_dim=2)
        p.fit([np.array([0.0, 0.0]), np.array([1.0, 1.0])])
        means, vars_ = p.predict(horizon=2)
        self.assertEqual(means.shape, (3, 2))

    def test_uncertainty_initial(self):
        p = StatePredictor(state_dim=2)
        self.assertEqual(p.uncertainty(), 1.0)

    def test_uncertainty_after_fit(self):
        p = StatePredictor(state_dim=2)
        p.fit([np.array([0.0, 0.0]), np.array([1.0, 1.0])])
        u = p.uncertainty()
        self.assertGreaterEqual(u, 0.0)

    def test_confidence(self):
        p = StatePredictor(state_dim=2)
        self.assertEqual(p.confidence(), 0.0)

    def test_confidence_range(self):
        p = StatePredictor(state_dim=2)
        p.fit([np.array([0.0, 0.0]), np.array([1.0, 1.0])])
        c = p.confidence()
        self.assertGreaterEqual(c, 0.0)
        self.assertLessEqual(c, 1.0)


class TestTimeSeriesForecaster(unittest.TestCase):
    def test_init(self):
        f = TimeSeriesForecaster(window=5)
        self.assertEqual(f.window, 5)
        self.assertEqual(f.data, [])

    def test_forecast_empty(self):
        f = TimeSeriesForecaster()
        mean, std = f.forecast(horizon=3)
        self.assertEqual(len(mean), 3)
        self.assertEqual(len(std), 3)

    def test_forecast_insufficient_data(self):
        f = TimeSeriesForecaster(window=5)
        f.add_point(1.0)
        mean, std = f.forecast(horizon=3)
        self.assertEqual(mean, [1.0, 1.0, 1.0])
        self.assertEqual(std, [1.0, 1.0, 1.0])

    def test_forecast(self):
        f = TimeSeriesForecaster(window=3)
        for v in [1.0, 2.0, 3.0, 4.0]:
            f.add_point(v)
        mean, std = f.forecast(horizon=2)
        self.assertEqual(len(mean), 2)
        self.assertEqual(len(std), 2)
        expected_mean = (2.0 + 3.0 + 4.0) / 3
        for m in mean:
            self.assertAlmostEqual(m, expected_mean)


if __name__ == "__main__":
    unittest.main()
