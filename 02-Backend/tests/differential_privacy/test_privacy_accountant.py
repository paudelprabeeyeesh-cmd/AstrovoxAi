from differential_privacy.privacy_accountant import PrivacyAccountant
from differential_privacy.gaussian_mechanism import GaussianMechanism
from differential_privacy.laplace_mechanism import LaplaceMechanism


def test_privacy_accountant_empty():
    accountant = PrivacyAccountant()
    budget = accountant.total_budget()
    assert budget.epsilon == 0.0
    assert budget.delta == 0.0


def test_privacy_accountant_single_mechanism():
    accountant = PrivacyAccountant()
    mechanism = GaussianMechanism(sensitivity=1.0, epsilon=1.0, delta=1e-5)
    accountant.add(mechanism)
    budget = accountant.total_budget()
    assert budget.epsilon == 1.0
    assert budget.delta == 1e-5


def test_privacy_accountant_multiple_mechanisms():
    accountant = PrivacyAccountant()
    accountant.add(GaussianMechanism(sensitivity=1.0, epsilon=1.0, delta=1e-5))
    accountant.add(LaplaceMechanism(sensitivity=1.0, epsilon=0.5))
    budget = accountant.total_budget()
    assert budget.epsilon == 1.5
    assert budget.delta == 1e-5


def test_privacy_accountant_max_delta():
    accountant = PrivacyAccountant()
    accountant.add(GaussianMechanism(sensitivity=1.0, epsilon=1.0, delta=1e-5))
    accountant.add(GaussianMechanism(sensitivity=1.0, epsilon=0.5, delta=1e-3))
    budget = accountant.total_budget()
    assert budget.epsilon == 1.5
    assert budget.delta == 1e-3
