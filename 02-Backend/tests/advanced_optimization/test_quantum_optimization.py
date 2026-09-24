import numpy as np
import pytest
from advanced_optimization.quantum_optimization import (
    simulated_quantum_annealing,
    quantum_inspired_population,
    qaoa_layer,
)


def test_simulated_quantum_annealing():
    f = lambda x: np.sum((x - 2) ** 2)
    x = simulated_quantum_annealing(f, np.array([0.0]), steps=500)
    assert np.allclose(x, 2.0, atol=1.0)


def test_quantum_inspired_population():
    f = lambda x: np.sum((x - 1) ** 2)
    bounds = [(-5, 5), (-5, 5)]
    x = quantum_inspired_population(f, bounds, pop_size=20, max_iter=30)
    assert np.allclose(x, 1.0, atol=1.0)


def test_qaoa_layer_shape():
    n = 2
    cost_mat = np.array([[1.0, 0.5], [0.5, 1.0]])
    mixer_mat = np.eye(2 ** n)
    params = np.random.randn(4)
    probs = qaoa_layer(params, cost_mat, mixer_mat, depth=2)
    assert probs.shape == (2 ** n,)
    assert abs(np.sum(probs) - 1.0) < 1e-6
