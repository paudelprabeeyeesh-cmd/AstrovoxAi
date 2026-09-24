import math

from differential_privacy.laplace_mechanism import LaplaceMechanism


def test_laplace_mechanism_initialization():
    mechanism = LaplaceMechanism(sensitivity=1.0, epsilon=1.0)
    assert mechanism.sensitivity == 1.0
    assert mechanism.epsilon == 1.0


def test_laplace_mechanism_scale():
    mechanism = LaplaceMechanism(sensitivity=1.0, epsilon=1.0)
    assert abs(mechanism.b - 1.0) < 1e-10


def test_laplace_mechanism_release():
    mechanism = LaplaceMechanism(sensitivity=1.0, epsilon=1.0)
    released = mechanism.release(5.0)
    assert isinstance(released, float)
    assert released != 5.0


def test_laplace_mechanism_budget():
    mechanism = LaplaceMechanism(sensitivity=1.0, epsilon=1.0)
    budget = mechanism.budget()
    assert budget.epsilon == 1.0
    assert budget.delta == 0.0
