from meta_learning_advanced.meta_regularizer import MetaRegularizer, RegularizationConfig


def test_l2_penalty_zero_when_lambda_zero():
    params = {"W": 1.0}
    config = RegularizationConfig(l2_lambda=0.0)
    reg = MetaRegularizer(config)
    assert reg.l2_penalty(params) == 0.0


def test_l2_penalty_positive():
    params = {"W": 2.0}
    config = RegularizationConfig(l2_lambda=1.0)
    reg = MetaRegularizer(config)
    penalty = reg.l2_penalty(params)
    expected = float(4.0)
    assert penalty == expected


def test_weight_decay_penalty_no_prior():
    params = {"W": 1.0}
    config = RegularizationConfig(weight_decay_lambda=1.0, prior_params=None)
    reg = MetaRegularizer(config)
    assert reg.weight_decay_penalty(params) == 0.0


def test_weight_decay_penalty_with_prior():
    params = {"W": 2.0}
    prior = {"W": 0.0}
    config = RegularizationConfig(weight_decay_lambda=2.0, prior_params=prior)
    reg = MetaRegularizer(config)
    penalty = reg.weight_decay_penalty(params)
    expected = 2.0 * float(4.0)
    assert penalty == expected


def test_consistency_penalty_insufficient_params():
    config = RegularizationConfig(consistency_lambda=1.0)
    reg = MetaRegularizer(config)
    assert reg.consistency_penalty([]) == 0.0
    assert reg.consistency_penalty([{"W": 1.0}]) == 0.0


def test_consistency_penalty_identical_params():
    params = {"W": 1.0}
    config = RegularizationConfig(consistency_lambda=1.0)
    reg = MetaRegularizer(config)
    assert reg.consistency_penalty([params, params]) == 0.0


def test_consistency_penalty_different_params():
    p1 = {"W": 1.0}
    p2 = {"W": 0.0}
    config = RegularizationConfig(consistency_lambda=1.0)
    reg = MetaRegularizer(config)
    penalty = reg.consistency_penalty([p1, p2])
    expected = float(1.0)
    assert penalty == expected


def test_compute_total():
    params = {"W": 1.0}
    prior = {"W": 0.0}
    adapted = [{"W": 1.0}, {"W": 0.0}]
    config = RegularizationConfig(l2_lambda=1.0, weight_decay_lambda=2.0, consistency_lambda=3.0, prior_params=prior)
    reg = MetaRegularizer(config)
    total = reg.compute_total(params, adapted_params_list=adapted)
    expected = reg.l2_penalty(params) + reg.weight_decay_penalty(params) + reg.consistency_penalty(adapted)
    assert total == expected


def test_compute_total_without_adapted():
    params = {"W": 1.0}
    config = RegularizationConfig(l2_lambda=1.0)
    reg = MetaRegularizer(config)
    total = reg.compute_total(params)
    assert total == reg.l2_penalty(params)
