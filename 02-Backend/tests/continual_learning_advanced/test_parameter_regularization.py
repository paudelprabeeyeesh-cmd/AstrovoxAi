import math
import pytest
from continual_learning_advanced.parameter_regularization import ParameterRegularization, RegularizationConfig


class TestParameterRegularization:
    def test_initialization(self):
        pr = ParameterRegularization()
        assert pr.config.l2_lambda == 0.01
        assert pr.config.ewc_lambda == 100.0
        assert pr.optimal_params == {}

    def test_set_optimal_params(self):
        pr = ParameterRegularization()
        pr.set_optimal_params({"W": [1.0, 2.0], "b": [0.0]})
        assert pr.optimal_params["W"] == [1.0, 2.0]

    def test_compute_fisher(self):
        pr = ParameterRegularization()
        pr.compute_fisher({"W": [1.0, 2.0]}, {"W": [0.5, -0.5]})
        assert pr.fisher["W"] == [0.25, 0.25]

    def test_l2_penalty(self):
        pr = ParameterRegularization()
        pr.set_optimal_params({"W": [1.0, 2.0]})
        penalty = pr.l2_penalty({"W": [2.0, 3.0]})
        expected = 0.01 * ((1.0 ** 2) + (1.0 ** 2))
        assert math.isclose(penalty, expected)

    def test_l2_penalty_zero_at_optimum(self):
        pr = ParameterRegularization()
        pr.set_optimal_params({"W": [1.0, 2.0]})
        penalty = pr.l2_penalty({"W": [1.0, 2.0]})
        assert penalty == 0.0

    def test_ewc_penalty(self):
        pr = ParameterRegularization()
        pr.set_optimal_params({"W": [1.0, 2.0]})
        pr.compute_fisher({"W": [1.0, 2.0]}, {"W": [0.5, 0.5]})
        penalty = pr.ewc_penalty({"W": [1.5, 2.5]})
        expected = 0.5 * 100.0 * sum(f * (d ** 2) for f, d in zip([0.25, 0.25], [0.5, 0.5]))
        assert math.isclose(penalty, expected)

    def test_combined_penalty(self):
        pr = ParameterRegularization(RegularizationConfig(l2_lambda=0.1, ewc_lambda=1.0, si_lambda=0.0))
        pr.set_optimal_params({"W": [1.0]})
        pr.compute_fisher({"W": [1.0]}, {"W": [0.0]})
        penalty = pr.combined_penalty({"W": [2.0]})
        assert penalty > 0.0

    def test_consolidate_and_get_task_regularization(self):
        pr = ParameterRegularization()
        params = {"W": [1.0, 2.0]}
        pr.set_optimal_params(params)
        pr.compute_fisher(params, {"W": [0.5, 0.5]})
        pr.consolidate_task(1, params)
        reg = pr.get_task_regularization(1, {"W": [1.5, 2.5]})
        assert "l2_penalty" in reg
        assert "ewc_penalty" in reg
        assert "total" in reg
        assert reg["l2_penalty"] > 0.0
        assert reg["ewc_penalty"] > 0.0

    def test_regularization_report_empty(self):
        pr = ParameterRegularization()
        report = pr.regularization_report()
        assert report["steps"] == 0.0
        assert report["avg_total"] == 0.0
