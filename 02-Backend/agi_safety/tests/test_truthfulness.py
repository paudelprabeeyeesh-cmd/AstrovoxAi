import numpy as np
import pytest
from agi_safety.truthfulness import CalibratedConfidence, HonestyIncentive, CalibrationPoint


class TestCalibratedConfidence:
    def setup_method(self):
        self.cal = CalibratedConfidence(num_bins=10)

    def test_initial_ece_zero(self):
        assert self.cal.expected_calibration_error() == 0.0

    def test_update_changes_bins(self):
        self.cal.update(0.8, 1)
        assert self.cal.bin_counts[8] == 1

    def test_ece_nonnegative(self):
        for i in range(20):
            self.cal.update(np.random.rand(), np.random.randint(0, 2))
        assert self.cal.expected_calibration_error() >= 0.0

    def test_reliability_diagram_returns_points(self):
        for i in range(30):
            self.cal.update(np.random.rand(), np.random.randint(0, 2))
        points = self.cal.reliability_diagram()
        assert len(points) > 0
        assert isinstance(points[0], CalibrationPoint)

    def test_reliability_diagram_values_in_range(self):
        for i in range(30):
            self.cal.update(np.random.rand(), np.random.randint(0, 2))
        points = self.cal.reliability_diagram()
        for p in points:
            assert 0.0 <= p.predicted_prob <= 1.0
            assert 0.0 <= p.actual_freq <= 1.0

    def test_perfect_calibration_low_ece(self):
        cal = CalibratedConfidence(num_bins=10)
        for _ in range(50):
            conf = np.random.rand()
            cal.update(conf, 1 if np.random.rand() < conf else 0)
        ece = cal.expected_calibration_error()
        assert ece >= 0.0


class TestHonestyIncentive:
    def setup_method(self):
        self.incentive = HonestyIncentive(truthfulness_weight=0.7, calibration_weight=0.3)

    def test_score_declaration_high_when_correct(self):
        score = self.incentive.score_declaration(0.9, True, "correct statement")
        assert 0.0 <= score <= 1.0

    def test_score_declaration_low_when_wrong(self):
        score = self.incentive.score_declaration(0.9, False, "wrong statement")
        assert score < 0.7

    def test_perfect_calibration_high_score(self):
        score = self.incentive.score_declaration(0.5, True, "statement")
        assert score > 0.4

    def test_honesty_stats_empty(self):
        stats = self.incentive.get_honesty_stats()
        assert stats["total"] == 0
        assert stats["avg_score"] == 0.0

    def test_honesty_stats_updated(self):
        self.incentive.score_declaration(0.9, True, "s1")
        self.incentive.score_declaration(0.8, False, "s2")
        stats = self.incentive.get_honesty_stats()
        assert stats["total"] == 2
        assert 0.0 <= stats["truthfulness_rate"] <= 1.0

    def test_score_in_range(self):
        for _ in range(10):
            score = self.incentive.score_declaration(np.random.rand(), bool(np.random.randint(0, 2)), "s")
            assert 0.0 <= score <= 1.0
