from multi_task_learning.gradient_balancer import GradientBalancer


def test_uniform_balancing():
    balancer = GradientBalancer(method="uniform")
    weights = balancer.balance({"task_a": 1.0, "task_b": 2.0})
    assert weights["task_a"] == 1.0
    assert weights["task_b"] == 1.0


def test_inverse_loss_balancing():
    balancer = GradientBalancer(method="inverse_loss")
    weights = balancer.balance({"task_a": 1.0, "task_b": 2.0})
    total = sum(weights.values())
    assert abs(total - 2.0) < 1e-9
    assert weights["task_a"] > weights["task_b"]


def test_inverse_loss_sum_to_tasks_count():
    balancer = GradientBalancer(method="inverse_loss")
    weights = balancer.balance({"a": 0.5, "b": 1.0, "c": 2.0})
    assert abs(sum(weights.values()) - 3.0) < 1e-9


def test_normalize_balancing():
    balancer = GradientBalancer(method="normalize")
    weights = balancer.balance({"a": 1.0, "b": 1.0})
    assert abs(weights["a"] - 0.5) < 1e-9
    assert abs(weights["b"] - 0.5) < 1e-9


def test_normalize_balancing_unequal():
    balancer = GradientBalancer(method="normalize")
    weights = balancer.balance({"a": 0.1, "b": 10.0})
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_unknown_method_raises():
    balancer = GradientBalancer(method="unknown")
    try:
        balancer.balance({"a": 1.0})
        assert False
    except ValueError:
        pass
