import numpy as np
from meta_learning_advanced.meta_regularizer import MetaRegularizer, RegularizationConfig


def test_l2_penalty_zero_when_lambda_zero():
    params = {"W": np.random.randn(2, 2).astype(np.float64)}
    config = RegularizationConfig(l2_lambda=0.0)
    reg = MetaRegularizer(config)
    assert reg.l2_penalty(params) == 0.0


def test_l2_penalty_positive():
    np.random.seed(42)
    params = {"W": np.random.randn(2, 2).astype(np.float64)}
    config = RegularizationConfig(l2_lambda=1.0)
    reg = MetaRegularizer(config)
    penalty = reg.l2_penalty(params)
    expected = float(np.sum(params["W"] ** 2))
    assert np.isclose(penalty, expected)


def test_weight_decay_penalty_no_prior():
    params = {"W": np.random.randn(2, 2).astype(np.float64)}
    config = RegularizationConfig(weight_decay_lambda=1.0, prior_params=None)
    reg = MetaRegularizer(config)
    assert reg.weight_decay_penalty(params) == 0.0


def test_weight_decay_penalty_with_prior():
    np.random.seed(42)
    params = {"W": np.random.randn(2, 2).astype(np.float64)}
    prior = {"W": np.zeros((2, 2), dtype=np.float64)}
    config = RegularizationConfig(weight_decay_lambda=2.0, prior_params=prior)
    reg = MetaRegularizer(config)
    penalty = reg.weight_decay_penalty(params)
    expected = 2.0 * float(np.sum((params["W"] - prior["W"]) ** 2))
    assert np.isclose(penalty, expected)


def test_consistency_penalty_insufficient_params():
    config = RegularizationConfig(consistency_lambda=1.0)
    reg = MetaRegularizer(config)
    assert reg.consistency_penalty([]) == 0.0
    assert reg.consistency_penalty([{"W": np.ones((2, 2))}]) == 0.0


def test_consistency_penalty_identical_params():
    params = {"W": np.ones((2, 2), dtype=np.float64)}
    config = RegularizationConfig(consistency_lambda=1.0)
    reg = MetaRegularizer(config)
    assert reg.consistency_penalty([params, params]) == 0.0


def test_consistency_penalty_different_params():
    p1 = {"W": np.ones((2, 2), dtype=np.float64)}
    p2 = {"W": np.zeros((2, 2), dtype=np.float64)}
    config = RegularizationConfig(consistency_lambda=1.0)
    reg = MetaRegularizer(config)
    penalty = reg.consistency_penalty([p1, p2])
    expected = float(np.sum((p1["W"] - p2["W"]) ** 2))
    assert np.isclose(penalty, expected)


def test_compute_total():
    params = {"W": np.ones((2, 2), dtype=np.float64)}
    prior = {"W": np.zeros((2, 2), dtype=np.float64)}
    adapted = [{"W": np.ones((2, 2), dtype=np.float64)}, {"W": np.zeros((2, 2), dtype=np.float64)}]
    config = RegularizationConfig(l2_lambda=1.0, weight_decay_lambda=2.0, consistency_lambda=3.0, prior_params=prior)
    reg = MetaRegularizer(config)
    total = reg.compute_total(params, adapted_params_list=adapted)
    expected = reg.l2_penalty(params) + reg.weight_decay_penalty(params) + reg.consistency_penalty(adapted)
    assert np.isclose(total, expected)


def test_compute_total_without_adapted():
    params = {"W": np.ones((2, 2), dtype=np.float64)}
    config = RegularizationConfig(l2_lambda=1.0)
    reg = MetaRegularizer(config)
    total = reg.compute_total(params)
    assert np.isclose(total, reg.l2_penalty(params))
