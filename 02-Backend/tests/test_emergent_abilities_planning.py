import numpy as np
import pytest
from emergent_abilities.planning_abilities import PlanningAbilityModel, PlanningEmergenceAnalyzer, PlanningResult


class TestPlanningAbilityModel:
    def test_plan_output(self):
        model = PlanningAbilityModel(state_dim=8, action_dim=4, horizon=5)
        initial = np.random.randn(8)
        goal = np.zeros(8)
        result = model.plan(initial, goal, num_actions=4)
        assert isinstance(result, PlanningResult)
        assert result.horizon == 5
        assert len(result.plan) <= 5

    def test_transition_output_shape(self):
        model = PlanningAbilityModel(state_dim=8, action_dim=4, horizon=5)
        state = np.random.randn(8)
        action = np.eye(4)[0]
        next_state = model.transition(state, action)
        assert next_state.shape == (8,)

    def test_value_estimate_range(self):
        model = PlanningAbilityModel(state_dim=8, action_dim=4, horizon=5)
        state = np.random.randn(8)
        value = model.value_estimate(state)
        assert np.isfinite(value)

    def test_compute_planning_horizon(self):
        model = PlanningAbilityModel(state_dim=8, action_dim=4, horizon=10)
        model_sizes = np.array([1e8, 1e9, 1e10, 1e11])
        task_difficulties = np.array([0.1, 0.3, 0.6, 0.9, 1.0])
        horizons = model.compute_planning_horizon(model_sizes, task_difficulties)
        assert len(horizons) == 4
        assert np.all(horizons >= 0.0)

    def test_plan_success_rate(self):
        model = PlanningAbilityModel(state_dim=8, action_dim=4, horizon=5)
        goal = np.zeros(8)
        results = [model.plan(np.random.randn(8), goal, num_actions=4) for _ in range(10)]
        successes = [r.success for r in results]
        success_rate = np.mean(successes)
        assert 0.0 <= success_rate <= 1.0


class TestPlanningEmergenceAnalyzer:
    def test_record_plan(self):
        analyzer = PlanningEmergenceAnalyzer()
        model = PlanningAbilityModel(state_dim=8, action_dim=4, horizon=5)
        result = model.plan(np.random.randn(8), np.zeros(8))
        analyzer.record_plan(result)
        assert len(analyzer.planning_results) == 1

    def test_success_rate_by_horizon(self):
        analyzer = PlanningEmergenceAnalyzer()
        model = PlanningAbilityModel(state_dim=8, action_dim=4, horizon=5)
        for _ in range(6):
            result = model.plan(np.random.randn(8), np.zeros(8))
            analyzer.record_plan(result)
        rates = analyzer.success_rate_by_horizon()
        assert len(rates) == 1
        assert 0.0 <= rates[0] <= 1.0

    def test_horizon_emergence_threshold(self):
        analyzer = PlanningEmergenceAnalyzer()
        for _ in range(5):
            model = PlanningAbilityModel(state_dim=8, action_dim=4, horizon=5)
            result = model.plan(np.random.randn(8), np.zeros(8))
            analyzer.record_plan(result)
        threshold = analyzer.horizon_emergence_threshold()
        assert threshold >= 0.0

    def test_empty_analyzer(self):
        analyzer = PlanningEmergenceAnalyzer()
        rates = analyzer.success_rate_by_horizon()
        assert len(rates) == 0
