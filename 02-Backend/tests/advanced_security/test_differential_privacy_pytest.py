import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from advanced_security.differential_privacy import (
    DifferentialPrivacy,
    GaussianMechanism,
    LaplaceMechanism,
    SparseMechanism,
)


def test_laplace_noise_distribution() -> None:
    mech = LaplaceMechanism(epsilon=1.0)
    noises = [mech.noise() for _ in range(200)]
    assert abs(sum(noises) / len(noises)) < 0.5


def test_differential_privacy_empty() -> None:
    dp = DifferentialPrivacy(epsilon=1.0)
    with pytest.raises(ValueError):
        dp.query([], mechanism="laplace")


def test_differential_privacy_invalid_mechanism() -> None:
    dp = DifferentialPrivacy(epsilon=1.0)
    with pytest.raises(ValueError):
        dp.query([1.0, 2.0], mechanism="invalid")


def test_histogram_sum_invariant() -> None:
    dp = DifferentialPrivacy(epsilon=1.0)
    data = [i % 5 for i in range(1000)]
    hist = dp.histogram(data, bins=5)
    assert len(hist) == 5
