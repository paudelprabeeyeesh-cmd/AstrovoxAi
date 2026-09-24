import numpy as np
from typing import Tuple, Optional
from .quantum_circuits import QuantumCircuit


class QuantumKernel:
    def __init__(self, encoding: str = "angle"):
        self.encoding = encoding

    def _encode_data(self, x: np.ndarray) -> QuantumCircuit:
        if self.encoding == "amplitude":
            circuit = QuantumCircuit(int(np.ceil(np.log2(len(x)))))
            from .quantum_embeddings import QuantumEmbedding
            QuantumEmbedding.amplitude_embedding(circuit, x)
            return circuit
        elif self.encoding == "angle":
            num_qubits = len(x)
            circuit = QuantumCircuit(num_qubits)
            for i in range(num_qubits):
                circuit.ry(i, x[i])
            return circuit
        else:
            num_qubits = int(np.ceil(np.log2(len(x))))
            circuit = QuantumCircuit(num_qubits)
            for i in range(min(len(x), num_qubits)):
                circuit.h(i)
                circuit.ry(i, x[i])
            return circuit

    def kernel(self, x: np.ndarray, y: np.ndarray) -> float:
        circuit_x = self._encode_data(x)
        circuit_y = self._encode_data(y)
        state_x = circuit_x.run()
        state_y = circuit_y.run()
        return float(np.abs(np.vdot(state_x, state_y))**2)

    def kernel_matrix(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        n, m = X.shape[0], Y.shape[0]
        K = np.zeros((n, m))
        for i in range(n):
            for j in range(m):
                K[i, j] = self.kernel(X[i], Y[j])
        return K


class QuantumSVM:
    def __init__(self, encoding: str = "angle", C: float = 1.0):
        self.encoding = encoding
        self.C = C
        self.kernel = QuantumKernel(encoding)
        self.alpha: Optional[np.ndarray] = None
        self.b: float = 0.0
        self.support_vectors: Optional[np.ndarray] = None
        self.support_labels: Optional[np.ndarray] = None

    def _kernel_matrix(self, X: np.ndarray) -> np.ndarray:
        n = X.shape[0]
        K = np.zeros((n, n))
        for i in range(n):
            for j in range(i, n):
                k_val = self.kernel.kernel(X[i], X[j])
                K[i, j] = k_val
                K[j, i] = k_val
        return K

    def fit(self, X: np.ndarray, y: np.ndarray, epochs: int = 100, lr: float = 0.01) -> "QuantumSVM":
        n = X.shape[0]
        K = self._kernel_matrix(X)
        self.alpha = np.zeros(n)
        y_float = y.astype(float)
        for _ in range(epochs):
            for i in range(n):
                decision = np.sum(self.alpha * y_float * K[:, i]) - self.b
                if y_float[i] * decision < 1:
                    self.alpha[i] += lr * (1 - y_float[i] * decision)
                    self.alpha[i] = np.clip(self.alpha[i], 0, self.C)
        sv_idx = self.alpha > 1e-6
        self.support_vectors = X[sv_idx]
        self.support_labels = y[sv_idx]
        if np.any(sv_idx):
            self.b = float(np.mean(y_float[sv_idx] - np.sum(self.alpha * y_float * K[:, sv_idx], axis=0)))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.alpha is None:
            raise ValueError("Model not fitted")
        predictions = np.zeros(X.shape[0])
        for i in range(X.shape[0]):
            decision = 0
            for j in range(len(self.support_vectors)):
                decision += self.alpha[j] * self.support_labels[j] * self.kernel.kernel(self.support_vectors[j], X[i])
            predictions[i] = 1 if decision - self.b > 0 else -1
        return predictions

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        preds = self.predict(X)
        return float(np.mean(preds == y))
