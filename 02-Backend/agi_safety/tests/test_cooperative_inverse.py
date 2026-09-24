import numpy as np
import pytest
from agi_safety.cooperative_inverse import (
    CooperativeInverseRL,
    PreferenceLearning,
    ValueEstimate,
    Preference,
)


class TestPreferenceLearning:
    def setup_method(self):
        self.learner = PreferenceLearning(state_dim=4, num_actions=3, learning_rate=0.1)

    def test_estimate_value_returns_estimate(self):
        state = np.array([0.1, -0.2, 0.3, -0.4])
        estimate = self.learner.estimate_value(state)
        assert isinstance(estimate, ValueEstimate)
        assert estimate.action_values.shape == (3,)

    def test_preferred_action_in_range(self):
        state = np.random.randn(4)
        estimate = self.learner.estimate_value(state)
        assert 0 <= estimate.preferred_action < 3

    def test_observe_preference_updates_stats(self):
        state = np.random.randn(4)
        self.learner.observe_preference(state, preferred=0, dispreferred=1, confidence=0.9)
        stats = self.learner.get_preference_stats()
        assert stats["total"] == 1
        assert stats["avg_confidence"] == 0.9

    def test_multiple_preferences(self):
        state = np.random.randn(4)
        for _ in range(5):
            self.learner.observe_preference(state, 0, 1, 0.9)
        stats = self.learner.get_preference_stats()
        assert stats["total"] == 5

    def test_empty_preferences_stats(self):
        stats = self.learner.get_preference_stats()
        assert stats["avg_confidence"] == 0.0


class TestCooperativeInverseRL:
    def setup_method(self):
        self.cirl = CooperativeInverseRL(state_dim=4, num_actions=3)

    def test_propose_action_in_range(self):
        state = np.random.randn(4)
        action = self.cirl.propose_action(state)
        assert 0 <= action < 3

    def test_receive_positive_feedback(self):
        state = np.array([0.1, 0.2, 0.3, 0.4])
        self.cirl.receive_feedback(state, 0, "good job")
        metrics = self.cirl.get_alignment_metrics()
        assert metrics["total_feedback"] == 1

    def test_receive_negative_feedback(self):
        state = np.array([0.1, 0.2, 0.3, 0.4])
        self.cirl.receive_feedback(state, 0, "bad action")
        metrics = self.cirl.get_alignment_metrics()
        assert metrics["total_feedback"] == 1

    def test_alignment_metrics_keys(self):
        metrics = self.cirl.get_alignment_metrics()
        assert "total_feedback" in metrics
        assert "positive_rate" in metrics

    def test_receive_multiple_feedback(self):
        state = np.array([0.1, 0.2, 0.3, 0.4])
        for i in range(5):
            self.cirl.receive_feedback(state, i % 3, "good" if i % 2 == 0 else "bad")
        metrics = self.cirl.get_alignment_metrics()
        assert metrics["total_feedback"] == 5

    def test_empty_feedback_metrics(self):
        metrics = self.cirl.get_alignment_metrics()
        assert metrics["total_feedback"] == 0
        assert metrics["positive_rate"] == 0.0
