import numpy as np
import pytest
from advanced_optimization.stochastic_opt import spsa, stochastic_approximation, KieferWolfowitz


def test_spsa_converges():
    f = lambda x: np.sum((x - 3) ** 2)
    x = spsa(f, np.array([0.0]), max_iter=200)
    assert np.allclose(x, 3.0, atol=1.0)


def test_stochastic_approximation_converges():
    f = lambda x: np.sum((x - 2) ** 2)
    x = stochastic_approximation(f, np.array([0.0]), lr=0.1, max_iter=200)
    assert np.allclose(x, 2.0, atol=1.0)


def test_kiefer_wolfowitz_converges():
    f = lambda x: np.sum((x - 1) ** 2)
    x = KieferWolfowitz(f, np.array([0.0]), lr=0.1, max_iter=100)
    assert np.allclose(x, 1.0, atol=1.0)
