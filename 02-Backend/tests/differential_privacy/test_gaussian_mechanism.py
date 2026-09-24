import math

from differential_privacy.gaussian_mechanism import GaussianMechanism


def test_gaussian_mechanism_initialization():
    mechanism = GaussianMechanism(sensitivity=1.0, epsilon=1.0, delta=1e-5)
    assert mechanism.sensitivity == 1.0
    assert mechanism.epsilon == 1.0
    assert mechanism.delta == 1e-5


def test_gaussian_mechanism_sigma():
    mechanism = GaussianMechanism(sensitivity=1.0, epsilon=1.0, delta=1e-5)
    expected_sigma = math.sqrt(2 * math.log(1.25 / 1e-5)) * 1.0 / 1.0
    assert abs(mechanism.sigma - expected_sigma) < 1e-10


def test_gaussian_mechanism_release():
    mechanism = GaussianMechanism(sensitivity=1.0, epsilon=1.0, delta=1e-5)
    released = mechanism.release(5.0)
    assert isinstance(released, float)
    assert released != 5.0


def test_gaussian_mechanism_budget():
    mechanism = GaussianMechanism(sensitivity=1.0, epsilon=1.0, delta=1e-5)
    budget = mechanism.budget()
    assert budget.epsilon == 1.0
    assert budget.delta == 1e-5


def test_gaussian_mechanism_initialization_different_values():
    mechanism = GaussianMechanism(sensitivity=2.0, epsilon=0.5, delta=1e-4)
    assert mechanism.sensitivity == 2.0
    assert mechanism.epsilon == 0.5
    assert mechanism.delta == 1e-4


def test_gaussian_mechanism_sigma_different_values():
    mechanism = GaussianMechanism(sensitivity=2.0, epsilon=0.5, delta=1e-4)
    expected_sigma = math.sqrt(2 * math.log(1.25 / 1e-4)) * 2.0 / 0.5
    assert abs(mechanism.sigma - expected_sigma) < 1e-10
