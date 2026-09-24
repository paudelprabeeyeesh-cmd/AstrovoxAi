import numpy as np
import pytest
from emergent_abilities.scaling_laws import ChinchillaScaling, ScalingLawAnalyzer, ScalingLawResult


class TestChinchillaScaling:
    def test_loss_decreases_with_params(self):
        scaling = ChinchillaScaling(a=1.5, b=0.65, e=2.0)
        loss_100m = scaling.loss(1e8, 1e9)
        loss_10b = scaling.loss(1e10, 1e10)
        assert loss_10b < loss_100m

    def test_loss_scales_with_tokens(self):
        scaling = ChinchillaScaling()
        loss_no_tokens = scaling.loss(1e9, 1e3)
        loss_many_tokens = scaling.loss(1e9, 1e10)
        assert loss_many_tokens < loss_no_tokens

    def test_optimal_model_size_returns_result(self):
        scaling = ChinchillaScaling()
        result = scaling.optimal_model_size(compute_budget=1e18)
        assert isinstance(result, ScalingLawResult)
        assert result.optimal_params > 0
        assert result.optimal_tokens > 0
        assert result.optimal_flops > 0

    def test_optimal_params_exceeds_budget(self):
        scaling = ChinchillaScaling()
        budget = 1e18
        result = scaling.optimal_model_size(budget)
        assert 6 * result.optimal_params * result.optimal_tokens == pytest.approx(result.optimal_flops, rel=1e-6)

    def test_compute_optimal_returns_dict(self):
        scaling = ChinchillaScaling()
        result = scaling.compute_optimal(compute_budget=1e18)
        assert "optimal_params" in result
        assert "optimal_tokens" in result
        assert "optimal_flops" in result
        assert "loss" in result

    def test_iso_compute_curve_length(self):
        scaling = ChinchillaScaling()
        curve = scaling.iso_compute_curve(compute_budget=1e18, num_points=20)
        assert len(curve) == 20
        assert np.all(np.isfinite(curve))

    def test_iso_compute_curve_decreases(self):
        scaling = ChinchillaScaling()
        curve = scaling.iso_compute_curve(compute_budget=1e18, num_points=20)
        assert curve[len(curve) // 2] < curve[0]


class TestScalingLawAnalyzer:
    def test_predict_loss(self):
        analyzer = ScalingLawAnalyzer()
        loss = analyzer.predict_loss(1e9, 1e9)
        assert np.isfinite(loss)
        assert loss > 0

    def test_scaling_exponent_estimate(self):
        analyzer = ScalingLawAnalyzer()
        model_sizes = np.logspace(8, 11, 10)
        losses = 2.0 + 1.0 / (model_sizes ** 0.65)
        exponent = analyzer.scaling_exponent_estimate(model_sizes, losses)
        assert 0.5 < exponent < 0.9

    def test_fit_chinchilla_params(self):
        analyzer = ScalingLawAnalyzer()
        n_values = np.logspace(8, 11, 10)
        d_values = n_values * 10
        loss_values = 2.0 + 1.0 / (n_values ** 0.65) + 1.0 / (d_values ** 0.65)
        params = analyzer.fit_chinchilla_params(n_values, d_values, loss_values)
        assert "a" in params
        assert "b" in params
        assert params["a"] > 0
        assert params["b"] > 0

    def test_compute_efficient_frontier(self):
        analyzer = ScalingLawAnalyzer()
        budgets = np.logspace(15, 21, 5)
        frontier = analyzer.compute_efficient_frontier(budgets)
        assert "params" in frontier
        assert "tokens" in frontier
        assert "losses" in frontier
        assert len(frontier["params"]) == 5
