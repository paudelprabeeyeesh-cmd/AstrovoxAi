import numpy as np
from typing import Callable, List, Tuple
from .quantum_circuits import QuantumCircuit


class ParameterizedQuantumCircuit:
    def __init__(self, num_qubits: int, num_layers: int):
        self.num_qubits = num_qubits
        self.num_layers = num_layers
        self.num_params = num_layers * num_qubits * 2
        self.params = np.random.randn(self.num_params) * 0.1

    def circuit(self, x: np.ndarray, params: np.ndarray) -> QuantumCircuit:
        circuit = QuantumCircuit(self.num_qubits)
        param_idx = 0
        for layer in range(self.num_layers):
            for i in range(self.num_qubits):
                if i < len(x):
                    circuit.ry(i, x[i])
            for i in range(self.num_qubits):
                circuit.ry(i, params[param_idx])
                param_idx += 1
            for i in range(self.num_qubits):
                circuit.rz(i, params[param_idx])
                param_idx += 1
            for i in range(0, self.num_qubits - 1, 2):
                circuit.cnot(i, i + 1)
            for i in range(1, self.num_qubits - 1, 2):
                circuit.cnot(i, i + 1)
        return circuit

    def forward(self, x: np.ndarray, params: Optional[np.ndarray] = None) -> np.ndarray:
        if params is None:
            params = self.params
        circuit = self.circuit(x, params)
        state = circuit.run()
        probs = np.abs(state)**2
        return probs

    def gradient(self, x: np.ndarray, params: Optional[np.ndarray] = None, eps: float = 1e-6) -> np.ndarray:
        if params is None:
            params = self.params
        grad = np.zeros_like(params)
        for i in range(len(params)):
            p = params.copy()
            p[i] += eps
            f1 = self.forward(x, params)
            f2 = self.forward(x, p)
            grad[i] = np.sum((f2 - f1) / eps)
        return grad

    def measure_expectation(self, x: np.ndarray, observable: np.ndarray, params: Optional[np.ndarray] = None) -> float:
        state = self.forward(x, params)
        return float(np.real(state @ observable @ state))

    def loss(self, x: np.ndarray, y: float, params: Optional[np.ndarray] = None) -> float:
        probs = self.forward(x, params)
        pred = float(np.sum(probs[:len(probs)//2]))
        return (pred - y) ** 2

    def train_step(self, x: np.ndarray, y: float, lr: float = 0.01) -> float:
        grad = self.gradient(x)
        self.params = self.params - lr * grad
        return self.loss(x, y)
