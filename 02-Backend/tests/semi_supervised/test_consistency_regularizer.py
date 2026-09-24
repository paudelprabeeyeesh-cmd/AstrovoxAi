import math

from semi_supervised.consistency_regularizer import ConsistencyRegularizer


def test_consistency_identical_inputs():
    reg = ConsistencyRegularizer()
    logits = [[1.0, 2.0, 3.0], [0.5, 1.5, 2.5]]
    loss = reg(logits, logits)
    assert math.isclose(loss, 0.0, abs_tol=1e-9)


def test_consistency_different_inputs():
    reg = ConsistencyRegularizer()
    logits1 = [[1.0, 2.0, 3.0]]
    logits2 = [[3.0, 2.0, 1.0]]
    loss = reg(logits1, logits2)
    assert loss > 0.0


def test_consistency_temperature():
    reg = ConsistencyRegularizer(temperature=0.5)
    logits1 = [[1.0, 2.0, 3.0]]
    logits2 = [[3.0, 2.0, 1.0]]
    loss = reg(logits1, logits2)
    assert isinstance(loss, float)
    assert loss > 0.0
