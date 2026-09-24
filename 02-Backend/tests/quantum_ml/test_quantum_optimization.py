import numpy as np
import pytest
from quantum_ml.quantum_optimization import QuantumGradientDescent, QuantumOptimizer


class TestQuantumGradientDescent:
    def test_finite_difference_gradient(self):
        def f(x):
            return x[0]**2 + x[1]**2
        params = np.array([1.0, 2.0])
        grad = QuantumGradientDescent.finite_difference(f, params)
        np.testing.assert_allclose(grad, np.array([2.0, 4.0]), atol=1e-4)

    def test_parameter_shift(self):
        def f(x):
            return np.sin(x[0])
        params = np.array([np.pi / 4])
        grad = QuantumGradientDescent.parameter_shift(f, params)
        expected = np.cos(np.pi / 4)
        np.testing.assert_allclose(grad, np.array([expected]), atol=1e-4)

    def test_sarsa_minimizes(self):
        def f(x):
            return np.sum(x**2)
        params = np.array([5.0, -3.0])
        result = QuantumGradientDescent.sarsa(f, params, lr=0.05, iterations=2000)
        assert np.linalg.norm(result) < 1.5

    def test_adam_minimizes(self):
        def f(x):
            return np.sum(x**2)
        params = np.array([3.0, -2.0])
        result = QuantumGradientDescent.adam(f, params, iterations=2000)
        assert np.linalg.norm(result) < 1.5

    def test_sarsa_different_runs(self):
        def f(x):
            return np.sum(x**2)
        params = np.array([1.0, 1.0])
        result = QuantumGradientDescent.sarsa(f, params, iterations=50, lr=0.1)
        assert len(result) == 2


class TestQuantumOptimizer:
    def test_gd_minimizes(self):
        opt = QuantumOptimizer(method="gd")
        def f(x):
            return np.sum((x - 1)**2)
        params = np.zeros(3)
        result = opt.minimize(f, params, iterations=50, lr=0.1)
        assert np.linalg.norm(result - 1) < 0.5

    def test_spsa_minimizes(self):
        opt = QuantumOptimizer(method="spsa")
        def f(x):
            return np.sum(x**2)
        params = np.array([2.0, -2.0])
        result = opt.minimize(f, params, iterations=5000)
        assert np.linalg.norm(result) < 1.5

    def test_adam_minimizes(self):
        opt = QuantumOptimizer(method="adam")
        def f(x):
            return np.sum(x**2)
        params = np.array([3.0, -3.0])
        result = opt.minimize(f, params, iterations=5000)
        assert np.linalg.norm(result) < 1.5

    def test_unknown_method_raises(self):
        opt = QuantumOptimizer(method="unknown")
        with pytest.raises(ValueError):
            opt.minimize(lambda x: np.sum(x**2), np.zeros(2), iterations=10)

    def test_line_search(self):
        opt = QuantumOptimizer()
        def f(x):
            return np.sum((x - 1)**2)
        direction = np.array([1.0, 0.0])
        params = np.array([0.0, 0.0])
        alpha = opt.line_search(f, params, direction)
        assert alpha > 0
        assert alpha <= 1.0
