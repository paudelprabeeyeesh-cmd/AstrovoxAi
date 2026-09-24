import numpy as np
from typing import Callable, Optional
from .quantum_circuits import QuantumCircuit


class QuantumGradientDescent:
    @staticmethod
    def parameter_shift(circuit_fn: Callable[[np.ndarray], float], params: np.ndarray, shift: float = np.pi / 2) -> np.ndarray:
        grad = np.zeros_like(params)
        for i in range(len(params)):
            p_plus = params.copy()
            p_minus = params.copy()
            p_plus[i] += shift
            p_minus[i] -= shift
            grad[i] = (circuit_fn(p_plus) - circuit_fn(p_minus)) / (2 * np.sin(shift))
        return grad

    @staticmethod
    def finite_difference(fn: Callable[[np.ndarray], float], params: np.ndarray, eps: float = 1e-5) -> np.ndarray:
        grad = np.zeros_like(params)
        for i in range(len(params)):
            p = params.copy()
            p[i] += eps
            grad[i] = (fn(p) - fn(params)) / eps
        return grad

    @staticmethod
    def sarsa(circuit_fn: Callable[[np.ndarray], float], initial_params: np.ndarray, lr: float = 0.01, noise_scale: float = 0.01, iterations: int = 100) -> np.ndarray:
        params = initial_params.copy()
        for _ in range(iterations):
            noise = np.random.randn(*params.shape) * noise_scale
            params_plus = params + noise
            params_minus = params - noise
            f_plus = circuit_fn(params_plus)
            f_minus = circuit_fn(params_minus)
            grad = (f_plus - f_minus) / (2 * noise_scale) * noise
            params = params - lr * grad
        return params

    @staticmethod
    def adam(fn: Callable[[np.ndarray], float], initial_params: np.ndarray, lr: float = 0.001, beta1: float = 0.9, beta2: float = 0.999, epsilon: float = 1e-8, iterations: int = 100) -> np.ndarray:
        params = initial_params.copy()
        m = np.zeros_like(params)
        v = np.zeros_like(params)
        t = 0
        for _ in range(iterations):
            t += 1
            grad = QuantumGradientDescent.finite_difference(fn, params)
            m = beta1 * m + (1 - beta1) * grad
            v = beta2 * v + (1 - beta2) * grad**2
            m_hat = m / (1 - beta1**t)
            v_hat = v / (1 - beta2**t)
            params = params - lr * m_hat / (np.sqrt(v_hat) + epsilon)
        return params


class QuantumOptimizer:
    def __init__(self, method: str = "gd"):
        self.method = method

    def minimize(self, fn: Callable[[np.ndarray], float], initial_params: np.ndarray, lr: float = 0.01, iterations: int = 100) -> np.ndarray:
        if self.method == "gd":
            return self._gradient_descent(fn, initial_params, lr, iterations)
        elif self.method == "spsa":
            return QuantumGradientDescent.sarsa(fn, initial_params, lr, iterations=iterations)
        elif self.method == "adam":
            return QuantumGradientDescent.adam(fn, initial_params, iterations=iterations)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _gradient_descent(self, fn: Callable[[np.ndarray], float], params: np.ndarray, lr: float, iterations: int) -> np.ndarray:
        for _ in range(iterations):
            grad = QuantumGradientDescent.finite_difference(fn, params)
            params = params - lr * grad
        return params

    def line_search(self, fn: Callable[[np.ndarray], float], params: np.ndarray, direction: np.ndarray, alpha: float = 0.3) -> float:
        t = 1.0
        while fn(params + t * direction) > fn(params) - alpha * t * np.dot(direction, direction):
            t *= 0.5
        return t
