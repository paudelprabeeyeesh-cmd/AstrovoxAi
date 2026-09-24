import numpy as np
from agi_safety.safe_exploration import (
    SafeExplorer,
    SafetyConstraint,
    ExplorationStep,
)


class TestSafetyConstraint:
    def test_constraint_creation(self):
        def bound_fn(state):
            return float(np.max(np.abs(state)))
        constraint = SafetyConstraint(name="bound", threshold=1.0, fn=bound_fn)
        assert constraint.name == "bound"
        assert constraint.threshold == 1.0


class TestSafeExplorer:
    def setup_method(self):
        self.explorer = SafeExplorer(state_dim=5, num_actions=4, risk_threshold=0.3)

    def test_add_constraint(self):
        def bound_fn(state):
            return float(np.max(np.abs(state)))
        self.explorer.add_constraint(SafetyConstraint(name="bound", threshold=1.0, fn=bound_fn))
        assert len(self.explorer.constraints) == 1

    def test_compute_risk_returns_float(self):
        def bound_fn(state):
            return float(np.max(np.abs(state)))
        self.explorer.add_constraint(SafetyConstraint(name="bound", threshold=1.0, fn=bound_fn))
        risk = self.explorer.compute_risk(np.array([0.1, 0.2, 0.3, 0.4, 0.5]), 0)
        assert isinstance(risk, float)
        assert risk >= 0.0

    def test_select_action_in_range(self):
        action = self.explorer.select_action(np.array([0.1] * 5))
        assert 0 <= action < 4

    def test_explore_returns_step(self):
        def transition(s, a):
            return s + 0.01 * np.ones(5)
        step = self.explorer.explore(np.array([0.1] * 5), transition_fn=transition)
        assert isinstance(step, ExplorationStep)

    def test_step_fields_populated(self):
        def transition(s, a):
            return s
        step = self.explorer.explore(np.array([0.1] * 5), transition_fn=transition)
        assert step.action in range(4)
        assert 0.0 <= step.risk_score <= 1.0
        assert isinstance(step.allowed, bool)

    def test_exploration_stats_empty(self):
        stats = self.explorer.get_exploration_stats()
        assert stats["total"] == 0
        assert stats["allowed_rate"] == 0.0

    def test_exploration_stats_updated(self):
        def transition(s, a):
            return s
        for _ in range(10):
            self.explorer.explore(np.array([0.1] * 5), transition_fn=transition)
        stats = self.explorer.get_exploration_stats()
        assert stats["total"] == 10

    def test_risk_threshold_enforced(self):
        def dangerous_fn(state):
            return 10.0
        explorer = SafeExplorer(state_dim=2, num_actions=2, risk_threshold=0.5)
        explorer.add_constraint(SafetyConstraint(name="danger", threshold=1.0, fn=dangerous_fn))
        risk = explorer.compute_risk(np.array([1.0, 2.0]), 0)
        assert risk > explorer.risk_threshold
