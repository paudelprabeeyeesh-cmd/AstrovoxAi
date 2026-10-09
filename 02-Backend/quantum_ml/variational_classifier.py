import numpy as np
from typing import Optional
from .quantum_circuits import QuantumCircuit


class VariationalClassifier:
    def __init__(self, num_qubits: int, num_layers: int = 3):
        self.num_qubits = num_qubits
        self.num_layers = num_layers
        self.params = np.random.randn(num_layers * num_qubits * 2) * 0.1
        self.bias = 0.0

    def _ansatz(self, x: np.ndarray, params: np.ndarray) -> QuantumCircuit:
        circuit = QuantumCircuit(self.num_qubits)
        for i in range(self.num_qubits):
            circuit.ry(i, x[i % len(x)])
        idx = 0
        for _ in range(self.num_layers):
            for i in range(self.num_qubits):
                circuit.rz(i, params[idx])
                idx += 1
            for i in range(self.num_qubits - 1):
                circuit.cnot(i, i + 1)
            for i in range(self.num_qubits):
                circuit.ry(i, params[idx])
                idx += 1
        return circuit

    def predict_proba(self, x: np.ndarray) -> float:
        circuit = self._ansatz(x, self.params)
        state = circuit.run()
        probs = np.abs(state) ** 2
        return float(np.sum(probs[: 2 ** (self.num_qubits - 1)]))

    def predict(self, x: np.ndarray) -> int:
        return 1 if self.predict_proba(x) >= 0.5 else 0

    def fit(self, X: np.ndarray, y: np.ndarray, epochs: int = 50, lr: float = 0.01) -> "VariationalClassifier":
        for _ in range(epochs):
            grad = self._gradient(X, y, self.params)
            self.params -= lr * grad
        return self

    def _gradient(self, X: np.ndarray, y: np.ndarray, params: np.ndarray) -> np.ndarray:
        grad = np.zeros_like(params)
        eps = 1e-5
        for i in range(len(params)):
            p_plus = params.copy()
            p_minus = params.copy()
            p_plus[i] += eps
            p_minus[i] -= eps
            grad[i] = (self._loss(X, y, p_plus) - self._loss(X, y, p_minus)) / (2 * eps)
        return grad

    def _loss(self, X: np.ndarray, y: np.ndarray, params: np.ndarray) -> float:
        old_params = self.params.copy()
        self.params = params
        preds = np.array([self.predict_proba(x) for x in X])
        loss = float(np.mean((preds - y) ** 2))
        self.params = old_params
        return loss
