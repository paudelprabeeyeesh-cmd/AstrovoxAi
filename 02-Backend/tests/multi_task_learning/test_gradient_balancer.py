import math

import pytest
from multi_task_learning.gradient_balancer import GradientBalancer


class TestGradientBalancer:
    def test_uniform_returns_equal_weights(self):
        balancer = GradientBalancer(method="uniform")
        weights = balancer.balance({"task1": 1.0, "task2": 2.0})
        assert weights["task1"] == 1.0
        assert weights["task2"] == 1.0

    def test_inverse_loss_lower_loss_gets_higher_weight(self):
        balancer = GradientBalancer(method="inverse_loss")
        weights = balancer.balance({"task1": 0.1, "task2": 10.0})
        assert weights["task1"] > weights["task2"]

    def test_inverse_loss_weights_sum_to_n(self):
        balancer = GradientBalancer(method="inverse_loss")
        weights = balancer.balance({"task1": 1.0, "task2": 1.0})
        assert math.isclose(sum(weights.values()), 2.0, rel_tol=1e-9)

    def test_inverse_loss_single_task(self):
        balancer = GradientBalancer(method="inverse_loss")
        weights = balancer.balance({"task1": 5.0})
        assert math.isclose(weights["task1"], 1.0, rel_tol=1e-9)

    def test_normalize_method(self):
        balancer = GradientBalancer(method="normalize")
        weights = balancer.balance({"task1": 1.0, "task2": 3.0})
        assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-9)
        assert weights["task1"] > weights["task2"]

    def test_unknown_method_raises(self):
        balancer = GradientBalancer(method="unknown")
        with pytest.raises(ValueError, match="Unknown balancing method"):
            balancer.balance({"task1": 1.0})

    def test_default_method_is_inverse_loss(self):
        balancer = GradientBalancer()
        assert balancer.method == "inverse_loss"

    def test_inverse_loss_with_very_small_loss(self):
        balancer = GradientBalancer(method="inverse_loss")
        weights = balancer.balance({"task1": 1e-10, "task2": 1.0})
        assert not math.isnan(weights["task1"])
        assert not math.isnan(weights["task2"])

    def test_normalize_with_equal_losses(self):
        balancer = GradientBalancer(method="normalize")
        weights = balancer.balance({"task1": 1.0, "task2": 1.0})
        assert math.isclose(weights["task1"], weights["task2"], rel_tol=1e-9)

    def test_task_loss_history_tracking(self):
        balancer = GradientBalancer(method="uniform")
        balancer.balance({"task1": 1.0, "task2": 2.0})
        assert isinstance(balancer.task_loss_history, dict)
