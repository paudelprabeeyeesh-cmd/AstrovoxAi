import numpy as np
import pytest
from quantum_ml.quantum_optimizer import QuantumNaturalGradient, ParameterShiftOptimizer, QuantumOptimizer


class TestQuantumNaturalGradient:
    def test_metric_tensor_shape(self):
        fn = lambda p: p[0] ** 2 + p[1] ** 2
        params = np.array([1.0, 2.0])
        g = QuantumNaturalGradient.metric_tensor(fn, params)
        assert g.shape == (2, 2)

    def test_metric_tensor_positive(self):
        fn = lambda p: p[0] ** 2 + p[1] ** 2
        params = np.array([1.0, 2.0])
        g = QuantumNaturalGradient.metric_tensor(fn, params)
        eigenvals = np.linalg.eigvalsh(g)
        assert all(eigenvals > 0)

    def test_step_reduces_loss(self):
        fn = lambda p: (p[0] - 2) ** 2 + (p[1] + 1) ** 2
        params = np.array([0.0, 0.0])
        new_params = QuantumNaturalGradient.step(fn, params, lr=0.1)
        assert fn(new_params) < fn(params)

    def test_step_shape(self):
        fn = lambda p: np.sum(p ** 2)
        params = np.array([1.0, 2.0, 3.0])
        new_params = QuantumNaturalGradient.step(fn, params, lr=0.01)
        assert new_params.shape == params.shape


class TestParameterShiftOptimizer:
    def test_step_reduces_loss(self):
        fn = lambda p: (p[0] - 2) ** 2 + (p[1] + 1) ** 2
        params = np.array([0.0, 0.0])
        new_params = ParameterShiftOptimizer.step(fn, params, lr=0.1)
        assert fn(new_params) < fn(params)

    def test_step_shape(self):
        fn = lambda p: np.sum(p ** 2)
        params = np.array([1.0, 2.0, 3.0])
        new_params = ParameterShiftOptimizer.step(fn, params, lr=0.01)
        assert new_params.shape == params.shape

    def test_step_converges_toward_zero(self):
        fn = lambda p: np.sum(p ** 2)
        params = np.array([1.0, 1.0])
        for _ in range(20):
            params = ParameterShiftOptimizer.step(fn, params, lr=0.1)
        assert np.linalg.norm(params) < 0.5


class TestQuantumOptimizer:
    def test_natural_gradient_minimize(self):
        fn = lambda p: (p[0] - 2) ** 2 + (p[1] + 1) ** 2
        optimizer = QuantumOptimizer(method="natural_gradient")
        params = np.array([0.0, 0.0])
        result = optimizer.minimize(fn, params, lr=0.1, iterations=20)
        assert fn(result) < fn(params)

    def test_parameter_shift_minimize(self):
        fn = lambda p: (p[0] - 2) ** 2 + (p[1] + 1) ** 2
        optimizer = QuantumOptimizer(method="parameter_shift")
        params = np.array([0.0, 0.0])
        result = optimizer.minimize(fn, params, lr=0.1, iterations=20)
        assert fn(result) < fn(params)

    def test_unknown_method_raises(self):
        optimizer = QuantumOptimizer(method="unknown")
        fn = lambda p: np.sum(p ** 2)
        params = np.array([0.0, 0.0])
        with pytest.raises(ValueError):
            optimizer.minimize(fn, params)

    def test_natural_gradient_shape(self):
        fn = lambda p: np.sum(p ** 2)
        optimizer = QuantumOptimizer(method="natural_gradient")
        params = np.array([1.0, 2.0, 3.0])
        result = optimizer.minimize(fn, params, lr=0.01, iterations=10)
        assert result.shape == params.shape
