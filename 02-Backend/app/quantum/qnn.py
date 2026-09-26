import numpy as np
from typing import List
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator

@dataclass
class QuantumLayer:
    num_qubits: int
    weights: np.ndarray
    bias: np.ndarray

class QuantumNeuralNetwork:
    def __init__(self, layer_sizes: List[int]):
        self.layer_sizes = layer_sizes
        self.layers: List[QuantumLayer] = []
        for i in range(len(layer_sizes) - 1):
            w = np.random.randn(layer_sizes[i + 1], layer_sizes[i]) * 0.1
            b = np.zeros(layer_sizes[i + 1])
            self.layers.append(QuantumLayer(num_qubits=layer_sizes[i + 1], weights=w, bias=b))

    def _quantum_activation(self, x: np.ndarray) -> np.ndarray:
        sim = QuantumCircuitSimulator(min(len(x), 4))
        for i in range(min(len(x), 4)):
            sim.ry(i, np.clip(x[i], -np.pi, np.pi))
        probs = sim.get_probabilities()
        result = np.zeros(len(x))
        for i in range(len(x)):
            key = format(i % (2 ** min(len(x), 4)), f"0{min(len(x), 4)}b")
            result[i] = probs.get(key, 0.0) * 2 - 1
        return result

    def forward(self, x: np.ndarray) -> np.ndarray:
        for layer in self.layers:
            z = layer.weights @ x + layer.bias
            x = self._quantum_activation(z)
        return x

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 100, lr: float = 0.01) -> None:
        for epoch in range(epochs):
            total_loss = 0.0
            for i in range(len(X)):
                output = self.forward(X[i])
                loss = np.mean((output - y[i]) ** 2)
                total_loss += loss
                for layer in self.layers:
                    layer.weights -= lr * np.outer(output - y[i], X[i])
                    layer.bias -= lr * (output - y[i])
            if epoch % 20 == 0:
                print(f"Epoch {epoch}: loss={total_loss / len(X):.4f}")

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.array([self.forward(x) for x in X])

    def vqc_layer(self, x: np.ndarray, params: np.ndarray) -> np.ndarray:
        num_qubits = min(len(x), len(params))
        sim = QuantumCircuitSimulator(num_qubits)
        for i in range(num_qubits):
            sim.ry(i, x[i] * params[i])
        for i in range(num_qubits - 1):
            sim.cnot(i, i + 1)
        probs = sim.get_probabilities()
        return np.array([probs.get(format(i, f"0{num_qubits}b"), 0.0) for i in range(len(x))])

    def hybrid_layer(self, x: np.ndarray, quantum_params: np.ndarray, classical_params: np.ndarray) -> np.ndarray:
        quantum_out = self.vqc_layer(x, quantum_params)
        classical_out = classical_params @ x
        combined = 0.5 * quantum_out + 0.5 * classical_out
        return np.tanh(combined)

    def get_parameters(self) -> List[np.ndarray]:
        params = []
        for layer in self.layers:
            params.append(layer.weights.flatten())
            params.append(layer.bias)
        return np.concatenate(params)

    def set_parameters(self, params: np.ndarray) -> None:
        idx = 0
        for layer in self.layers:
            w_size = layer.weights.size
            layer.weights = params[idx: idx + w_size].reshape(layer.weights.shape)
            idx += w_size
            b_size = layer.bias.size
            layer.bias = params[idx: idx + b_size]
            idx += b_size
