import pytest
import numpy as np
from world_model.prediction import StatePredictor, TimeSeriesForecaster


class TestStatePredictor:
    def test_predict_returns_mean_and_variance(self):
        predictor = StatePredictor(state_dim=2)
        states = [np.array([1.0, 0.0]), np.array([1.1, 0.0]), np.array([1.2, 0.0])]
        predictor.fit(states)
        means, variances = predictor.predict(horizon=2)
        assert means.shape == (3, 2)
        assert variances.shape == (3,)

    def test_confidence_bounded(self):
        predictor = StatePredictor(state_dim=2)
        c = predictor.confidence()
        assert 0.0 <= c <= 1.0

    def test_uncertainty_non_negative(self):
        predictor = StatePredictor(state_dim=2)
        u = predictor.uncertainty()
        assert u >= 0.0


class TestTimeSeriesForecaster:
    def test_forecast_returns_lists(self):
        forecaster = TimeSeriesForecaster(window=3)
        for i in range(5):
            forecaster.add_point(float(i))
        means, stds = forecaster.forecast(horizon=2)
        assert len(means) == 2
        assert len(stds) == 2

    def test_forecast_mean_equals_last_window_mean(self):
        forecaster = TimeSeriesForecaster(window=3)
        for i in range(5):
            forecaster.add_point(float(i))
        means, _ = forecaster.forecast(horizon=1)
        expected = np.mean([2.0, 3.0, 4.0])
        assert means[0] == pytest.approx(expected)

    def test_forecast_single_point(self):
        forecaster = TimeSeriesForecaster(window=3)
        forecaster.add_point(5.0)
        means, stds = forecaster.forecast(horizon=2)
        assert len(means) == 2
        assert all(m == 5.0 for m in means)
