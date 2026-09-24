import numpy as np
import pytest
from agi_safety.impact_regularization import ImpactRegularizer, ImpactPenalty


class TestImpactRegularizer:
    def setup_method(self):
        self.regularizer = ImpactRegularizer(side_effect_weight=0.5, reversibility_weight=0.3)

    def test_no_change_low_penalty(self):
        state = np.array([1.0, 2.0, 3.0])
        penalty = self.regularizer.compute_penalty(state, state.copy(), action_cost=0.0)
        assert isinstance(penalty, ImpactPenalty)
        assert penalty.total < 0.1

    def test_large_change_high_penalty(self):
        before = np.array([0.0, 0.0, 0.0])
        after = np.array([10.0, 10.0, 10.0])
        penalty = self.regularizer.compute_penalty(before, after, action_cost=0.0)
        assert penalty.total > 0.0
        assert penalty.side_effects > 0.0

    def test_penalty_nonnegative(self):
        before = np.array([1.0, 2.0])
        after = np.array([2.0, 3.0])
        penalty = self.regularizer.compute_penalty(before, after, action_cost=0.1)
        assert penalty.total >= 0.0

    def test_side_effects_measurement(self):
        before = np.array([1.0, 2.0, 3.0])
        after = np.array([1.0, 2.0, 3.0])
        side_effects = self.regularizer.measure_side_effects(before, after)
        assert side_effects == 0.0

    def test_reversibility_score_range(self):
        before = np.array([1.0, 2.0])
        after = np.array([1.0, 2.0])
        score = self.regularizer.reversibility_score(before, after)
        assert 0.0 <= score <= 1.0

    def test_impact_stats_updated(self):
        before = np.array([1.0, 2.0])
        after = np.array([2.0, 3.0])
        self.regularizer.compute_penalty(before, after)
        stats = self.regularizer.get_impact_stats()
        assert stats["total"] == 1
        assert stats["avg_penalty"] > 0.0

    def test_action_cost_added(self):
        before = np.array([1.0])
        after = np.array([1.0])
        penalty = self.regularizer.compute_penalty(before, after, action_cost=0.5)
        assert penalty.base_penalty == 0.5

    def test_details_includes_norms(self):
        before = np.array([1.0, 2.0])
        after = np.array([3.0, 4.0])
        penalty = self.regularizer.compute_penalty(before, after)
        assert "delta_norm" in penalty.details
        assert "state_before_norm" in penalty.details
