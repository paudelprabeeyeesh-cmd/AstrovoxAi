import numpy as np
import pytest
from adaptive_learning.online_learning import OnlineLearner


class TestOnlineLearner:
    def test_initialization(self):
        ol = OnlineLearner(learning_rate=0.001, window_size=100)
        assert ol.learning_rate == 0.001
        assert ol.window_size == 100
        assert ol.weights is None

    def test_partial_fit(self):
        ol = OnlineLearner()
        x = np.random.randn(10, 4)
        y = np.random.randn(10, 1)
        loss = ol.partial_fit(x, y)
        assert isinstance(loss, float)
        assert ol.weights is not None

    def test_predict(self):
        ol = OnlineLearner()
        x = np.random.randn(10, 4)
        y = np.random.randn(10, 1)
        ol.partial_fit(x, y)
        preds = ol.predict(x)
        assert preds.shape == (10, 1)

    def test_window_management(self):
        ol = OnlineLearner(window_size=10)
        for _ in range(20):
            x = np.random.randn(1, 4)
            y = np.random.randn(1, 1)
            ol.partial_fit(x, y)
        assert len(ol.data_window) <= 10
        assert len(ol.loss_window) <= 10

    def test_drift_detection(self):
        ol = OnlineLearner()
        x = np.random.randn(1, 4)
        y = np.random.randn(1, 1)
        for _ in range(30):
            ol.partial_fit(x, y)
        report = ol.get_drift_report()
        assert "drift_detected" in report
        assert "drift_points" in report
        assert "step_count" in report

    def test_drift_points_recorded(self):
        ol = OnlineLearner()
        for _ in range(50):
            x = np.random.randn(1, 4)
            y = np.random.randn(1, 1)
            ol.partial_fit(x, y)
        assert isinstance(ol.drift_points, list)
