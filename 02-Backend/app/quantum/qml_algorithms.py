import numpy as np
from typing import Tuple, Optional
from .circuit_simulator import QuantumCircuitSimulator

class QuantumMachineLearning:
    def __init__(self, num_qubits: int, num_classes: int = 2):
        self.num_qubits = num_qubits
        self.num_classes = num_classes
        self.weights: Optional[np.ndarray] = None
        self.feature_map_params: Optional[np.ndarray] = None

    def encode_features(self, features: np.ndarray) -> QuantumCircuitSimulator:
        n = min(len(features), self.num_qubits)
        sim = QuantumCircuitSimulator(self.num_qubits)
        for i in range(n):
            sim.ry(i, features[i])
        return sim

    def variational_classifier(self, features: np.ndarray, weights: np.ndarray) -> np.ndarray:
        sim = self.encode_features(features)
        for i in range(self.num_qubits):
            sim.rz(i, weights[i])
            sim.ry(i, weights[i + self.num_qubits])
        for i in range(self.num_qubits - 1):
            sim.cnot(i, i + 1)
            sim.rz(i + 1, weights[i + 2 * self.num_qubits])
        probs = sim.get_probabilities()
        bitstring = max(probs, key=probs.get)
        return np.array([probs.get(format(i, f"0{self.num_qubits}b"), 0.0) for i in range(self.num_classes)])

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 100, lr: float = 0.01) -> np.ndarray:
        n_samples, n_features = X.shape
        self.weights = np.random.randn(3 * self.num_qubits) * 0.1
        for epoch in range(epochs):
            grads = np.zeros_like(self.weights)
            loss = 0.0
            for i in range(n_samples):
                probs = self.variational_classifier(X[i], self.weights)
                pred_class = int(np.argmax(probs[:self.num_classes]))
                target = int(y[i]) % self.num_classes
                loss += -np.log(probs[target] + 1e-10)
                error = probs.copy()
                error[target] -= 1
                for j in range(len(self.weights)):
                    self.weights[j] -= lr * error[target] * 0.01
            if epoch % 20 == 0:
                print(f"Epoch {epoch}: loss={loss / n_samples:.4f}")
        return self.weights

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.weights is None:
            raise ValueError("Model not trained")
        predictions = []
        for x in X:
            probs = self.variational_classifier(x, self.weights)
            predictions.append(int(np.argmax(probs[:self.num_classes])))
        return np.array(predictions)

    def qknn(self, query: np.ndarray, X_train: np.ndarray, y_train: np.ndarray, k: int = 3) -> int:
        distances = []
        for i, x in enumerate(X_train):
            sim_q = self.encode_features(query)
            sim_x = self.encode_features(x)
            fidelity = float(np.abs(np.dot(sim_q.get_statevector(), np.conj(sim_x.get_statevector()))))
            distances.append((1 - fidelity, y_train[i]))
        distances.sort(key=lambda d: d[0])
        k_nearest = [d[1] for d in distances[:k]]
        return int(np.bincount(k_nearest).argmax())

    def quantum_pca(self, X: np.ndarray, n_components: int = 2) -> Tuple[np.ndarray, np.ndarray]:
        cov = np.cov(X.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        idx = np.argsort(eigenvalues)[::-1]
        components = eigenvectors[:, idx[:n_components]]
        projected = X @ components
        return projected, components

    def qsvm_kernel(self, x1: np.ndarray, x2: np.ndarray) -> float:
        sim1 = self.encode_features(x1)
        sim2 = self.encode_features(x2)
        fidelity = float(np.abs(np.dot(sim1.get_statevector(), np.conj(sim2.get_statevector()))) ** 2)
        return fidelity

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> float:
        preds = self.predict(X)
        return float(np.mean(preds == y))
