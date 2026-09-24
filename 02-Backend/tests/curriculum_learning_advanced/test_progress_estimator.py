import pytest
from curriculum_learning_advanced.progress_estimator import ProgressEstimator, ProgressConfig


class TestProgressEstimator:
    def test_update(self):
        est = ProgressEstimator(ProgressConfig(window_size=5))
        for i in range(3):
            est.update(float(i))
        assert len(est.metrics) == 3

    def test_progress(self):
        est = ProgressEstimator()
        est.update(1.0)
        est.update(2.0)
        assert est.get_progress() == pytest.approx(1.0)

    def test_plateau_detection(self):
        est = ProgressEstimator(ProgressConfig(window_size=5, plateau_threshold=0.01))
        for _ in range(5):
            est.update(0.5)
        assert est.is_plateau()

    def test_estimate(self):
        est = ProgressEstimator()
        est.update(1.0)
        est.update(2.0)
        est.update(3.0)
        info = est.get_estimate()
        assert info["count"] == 3
        assert info["trend"] == pytest.approx(2.0)
