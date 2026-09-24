import numpy as np
from typing import Callable, Optional


class QuantumNaturalGradient:
    @staticmethod
    def metric_tensor(circuit_fn: Callable[[np.ndarray], float], params: np.ndarray, eps: float = 1e-4) -> np.ndarray:
        n = len(params)
        g = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                p1 = params.copy()
                p1[i] += eps
                p1[j] += eps
                p2 = params.copy()
                p2[i] += eps
                p3 = params.copy()
                p3[j] += eps
                g[i, j] = (circuit_fn(p1) - circuit_fn(p2) - circuit_fn(p3) + circuit_fn(params)) / (eps ** 2)
        return np.abs(g) + 1e-6 * np.eye(n)

    @staticmethod
    def step(fn: Callable[[np.ndarray], float], params: np.ndarray, lr: float = 0.01, eps: float = 1e-4) -> np.ndarray:
        grad = np.zeros_like(params)
        for i in range(len(params)):
            p = params.copy()
            p[i] += eps
            grad[i] = (fn(p) - fn(params)) / eps
        g = QuantumNaturalGradient.metric_tensor(fn, params, eps)
        step_dir = np.linalg.solve(g, grad)
        return params - lr * step_dir


class ParameterShiftOptimizer:
    @staticmethod
    def step(fn: Callable[[np.ndarray], float], params: np.ndarray, shift: float = np.pi / 4, lr: float = 0.01) -> np.ndarray:
        grad = np.zeros_like(params)
        for i in range(len(params)):
            p_plus = params.copy()
            p_minus = params.copy()
            p_plus[i] += shift
            p_minus[i] -= shift
            grad[i] = (fn(p_plus) - fn(p_minus)) / (2 * np.sin(shift))
        return params - lr * grad


class QuantumOptimizer:
    def __init__(self, method: str = "natural_gradient"):
        self.method = method

    def minimize(self, fn: Callable[[np.ndarray], float], initial_params: np.ndarray, lr: float = 0.01, iterations: int = 100) -> np.ndarray:
        params = initial_params.copy()
        if self.method == "natural_gradient":
            for _ in range(iterations):
                params = QuantumNaturalGradient.step(fn, params, lr)
        elif self.method == "parameter_shift":
            for _ in range(iterations):
                params = ParameterShiftOptimizer.step(fn, params, lr=lr)
        else:
            raise ValueError(f"Unknown method: {self.method}")
        return params
