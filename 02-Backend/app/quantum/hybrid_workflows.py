import numpy as np
from typing import List, Dict, Callable, Any
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator
from .qml_algorithms import QuantumMachineLearning
from .qrandom import QuantumRandomNumberGenerator

@dataclass
class HybridTask:
    name: str
    quantum_fn: Callable
    classical_fn: Callable
    combine_fn: Callable

class HybridQuantumWorkflow:
    def __init__(self, num_qubits: int = 4):
        self.num_qubits = num_qubits
        self.qml = QuantumMachineLearning(num_qubits)
        self.qrng = QuantumRandomNumberGenerator(num_qubits)

    def run(self, task: HybridTask, *args, **kwargs) -> Any:
        quantum_result = task.quantum_fn(*args, **kwargs)
        classical_result = task.classical_fn(*args, **kwargs)
        return task.combine_fn(quantum_result, classical_result)

    def optimization_workflow(self, objective_fn: Callable, bounds: List[Tuple[float, float]], max_iterations: int = 50) -> Dict:
        best_x = None
        best_f = float("inf")
        history = []
        for i in range(max_iterations):
            rand_vals = self.qrng.generate_uniform(len(bounds))
            x = []
            for j, (low, high) in enumerate(bounds):
                x.append(low + rand_vals[j] * (high - low))
            sim = QuantumCircuitSimulator(self.num_qubits)
            for j, val in enumerate(x):
                sim.ry(j, val * np.pi)
            f_val = objective_fn(np.array(x))
            if f_val < best_f:
                best_f = f_val
                best_x = x
            history.append({"iteration": i, "x": x, "f": f_val})
        return {"best_x": best_x, "best_f": best_f, "history": history}

    def ml_pipeline(self, X: np.ndarray, y: np.ndarray, task_type: str = "classification") -> Dict:
        if task_type == "classification":
            self.qml.train(X, y, epochs=50, lr=0.02)
            preds = self.qml.predict(X)
            accuracy = float(np.mean(preds == y))
            return {"accuracy": accuracy, "predictions": preds.tolist()}
        elif task_type == "qknn":
            preds = [self.qml.qknn(X[i], X, y, k=3) for i in range(len(X))]
            accuracy = float(np.mean(np.array(preds) == y))
            return {"accuracy": accuracy, "predictions": preds}
        return {}

    def feature_selection_workflow(self, X: np.ndarray, y: np.ndarray, n_features: int) -> List[int]:
        n_samples, n_total_features = X.shape
        scores = []
        for i in range(n_total_features):
            sim = QuantumCircuitSimulator(min(4, n_total_features))
            for j in range(min(4, n_total_features)):
                sim.ry(j, X[j % n_samples, i] * np.pi)
            fidelity_scores = []
            for k in range(n_samples):
                sim_k = QuantumCircuitSimulator(min(4, n_total_features))
                for j in range(min(4, n_total_features)):
                    sim_k.ry(j, X[k, j] * np.pi)
                sv1 = sim.get_statevector()
                sv2 = sim_k.get_statevector()
                min_dim = min(len(sv1), len(sv2))
                f = float(np.abs(np.dot(sv1[:min_dim], np.conj(sv2[:min_dim]))) ** 2)
                fidelity_scores.append(f)
            scores.append(np.mean(fidelity_scores))
        selected = np.argsort(scores)[::-1][:n_features].tolist()
        return selected

    def anomaly_detection_workflow(self, X: np.ndarray, threshold: float = 0.5) -> List[int]:
        anomalies = []
        for i in range(len(X)):
            sim = QuantumCircuitSimulator(self.num_qubits)
            for j in range(min(self.num_qubits, X.shape[1])):
                sim.ry(j, X[i, j] * np.pi)
            probs = sim.get_probabilities()
            max_prob = max(probs.values()) if probs else 0.0
            if max_prob < threshold:
                anomalies.append(i)
        return anomalies

    def clustering_workflow(self, X: np.ndarray, n_clusters: int = 2, max_iter: int = 20) -> Dict:
        centroids = X[np.random.choice(len(X), n_clusters, replace=False)]
        assignments = np.zeros(len(X), dtype=int)
        for iteration in range(max_iter):
            for i, x in enumerate(X):
                sim_x = QuantumCircuitSimulator(self.num_qubits)
                for j in range(min(self.num_qubits, len(x))):
                    sim_x.ry(j, x[j] * np.pi)
                sv_x = sim_x.get_statevector()
                distances = []
                for c in centroids:
                    sim_c = QuantumCircuitSimulator(self.num_qubits)
                    for j in range(min(self.num_qubits, len(c))):
                        sim_c.ry(j, c[j] * np.pi)
                    sv_c = sim_c.get_statevector()
                    min_dim = min(len(sv_x), len(sv_c))
                    dist = 1 - float(np.abs(np.dot(sv_x[:min_dim], np.conj(sv_c[:min_dim]))) ** 2)
                    distances.append(dist)
                assignments[i] = int(np.argmin(distances))
            new_centroids = []
            for k in range(n_clusters):
                cluster_points = X[assignments == k]
                if len(cluster_points) > 0:
                    new_centroids.append(cluster_points.mean(axis=0))
                else:
                    new_centroids.append(centroids[k])
            centroids = np.array(new_centroids)
        return {"centroids": centroids.tolist(), "assignments": assignments.tolist()}

    def generative_workflow(self, num_samples: int, latent_dim: int = 2) -> np.ndarray:
        samples = []
        for _ in range(num_samples):
            sim = QuantumCircuitSimulator(self.num_qubits)
            for i in range(self.num_qubits):
                theta = np.random.uniform(0, 2 * np.pi)
                sim.ry(i, theta)
            state = sim.get_statevector()
            samples.append(np.real(state[:latent_dim]))
        return np.array(samples)
