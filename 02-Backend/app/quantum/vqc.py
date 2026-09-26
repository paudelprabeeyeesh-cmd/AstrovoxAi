import numpy as np
from typing import Optional
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator

@dataclass
class VQCParameters:
    num_qubits: int
    num_layers: int
    params: np.ndarray

class VariationalQuantumCircuit:
    def __init__(self, num_qubits: int, num_layers: int = 3):
        self.num_qubits = num_qubits
        self.num_layers = num_layers
        self.num_params = num_layers * num_qubits * 2 + num_qubits
        self.params = np.random.randn(self.num_params) * 0.1

    def _build_circuit(self, params: np.ndarray, x: Optional[np.ndarray] = None) -> QuantumCircuitSimulator:
        sim = QuantumCircuitSimulator(self.num_qubits)
        if x is not None:
            for i in range(min(len(x), self.num_qubits)):
                sim.ry(i, x[i])
        idx = 0
        for layer in range(self.num_layers):
            for i in range(self.num_qubits):
                sim.ry(i, params[idx])
                sim.rz(i, params[idx + 1])
                idx += 2
            for i in range(self.num_qubits - 1):
                sim.cnot(i, i + 1)
        return sim

    def expectation_value(self, observable: Optional[np.ndarray] = None) -> float:
        sim = self._build_circuit(self.params)
        if observable is None:
            Z = np.kron(np.kron(np.eye(2), np.array([[1, 0], [0, -1]])), np.eye(2))
            observable = Z[: 2 ** self.num_qubits, : 2 ** self.num_qubits]
        return sim.expectation(observable)

    def cost(self, params: np.ndarray, x: np.ndarray, y: float) -> float:
        sim = self._build_circuit(params, x)
        probs = sim.get_probabilities()
        pred = sum(int(k, 2) * p for k, p in probs.items())
        return (pred - y) ** 2

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 100, lr: float = 0.01) -> np.ndarray:
        for epoch in range(epochs):
            grads = np.zeros_like(self.params)
            for i in range(len(X)):
                grad = self._numerical_gradient(self.params, X[i], y[i])
                grads += grad
            self.params -= lr * grads / len(X)
            if epoch % 20 == 0:
                loss = np.mean([self.cost(self.params, X[i], y[i]) for i in range(len(X))])
        return self.params

    def _numerical_gradient(self, params: np.ndarray, x: np.ndarray, y: float, eps: float = 1e-5) -> np.ndarray:
        grad = np.zeros_like(params)
        for i in range(len(params)):
            params_plus = params.copy()
            params_plus[i] += eps
            params_minus = params.copy()
            params_minus[i] -= eps
            grad[i] = (self.cost(params_plus, x, y) - self.cost(params_minus, x, y)) / (2 * eps)
        return grad

    def predict(self, X: np.ndarray) -> np.ndarray:
        predictions = []
        for x in X:
            sim = self._build_circuit(self.params, x)
            probs = sim.get_probabilities()
            pred = sum(int(k, 2) * p for k, p in probs.items())
            predictions.append(pred)
        return np.array(predictions)

    def get_statevector(self, x: Optional[np.ndarray] = None) -> np.ndarray:
        sim = self._build_circuit(self.params, x)
        return sim.get_statevector()

    def parameter_shift(self, params: np.ndarray, x: np.ndarray, y: float, observable: Optional[np.ndarray] = None) -> np.ndarray:
        grad = np.zeros_like(params)
        for i in range(len(params)):
            shift = np.zeros_like(params)
            shift[i] = np.pi / 2
            sim_plus = self._build_circuit(params + shift, x)
            sim_minus = self._build_circuit(params - shift, x)
            e_plus = sim_plus.expectation(observable)
            e_minus = sim_minus.expectation(observable)
            grad[i] = 0.5 * (e_plus - e_minus)
        return grad
