import numpy as np
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator
from .qml_algorithms import QuantumMachineLearning
from .qaoa import QAOA
from .qrandom import QuantumRandomNumberGenerator

@dataclass
class BenchmarkResult:
    name: str
    quantum_time: float
    classical_time: float
    quantum_accuracy: float
    classical_accuracy: float
    speedup: float
    advantage: float

class QuantumBenchmark:
    def __init__(self):
        self.results: List[BenchmarkResult] = []

    def benchmark_grover(self, target_state: int, num_qubits: int = 4) -> Dict:
        import time
        sim = QuantumCircuitSimulator(num_qubits)
        for i in range(num_qubits):
            sim.h(i)
        iterations = int(np.pi / 4 * np.sqrt(2 ** num_qubits))
        for _ in range(iterations):
            for i in range(num_qubits):
                if (target_state >> i) & 1:
                    sim.x(i)
            sim.toffoli(0, 1, 2) if num_qubits >= 3 else None
            for i in range(num_qubits):
                if (target_state >> i) & 1:
                    sim.x(i)
            for i in range(num_qubits):
                sim.h(i)
                sim.x(i)
            sim.toffoli(0, 1, 2) if num_qubits >= 3 else None
            for i in range(num_qubits):
                sim.x(i)
                sim.h(i)
        result = sim.run(shots=1024)
        found = max(result.counts, key=result.counts.get)
        return {
            "target": format(target_state, f"0{num_qubits}b"),
            "found": found,
            "success": int(found == format(target_state, f"0{num_qubits}b")),
            "iterations": iterations,
            "theoretical_iterations": int(np.pi / 4 * np.sqrt(2 ** num_qubits)),
        }

    def benchmark_qaoa(self, num_qubits: int = 4, depth: int = 2) -> Dict:
        import time
        qaoa = QAOA(num_qubits)
        hamiltonian = np.random.randn(2 ** num_qubits) + 1j * np.random.randn(2 ** num_qubits)
        start = time.time()
        result = qaoa.solve(hamiltonian, depth=depth, max_iterations=20)
        quantum_time = time.time() - start
        start = time.time()
        exact = np.linalg.eigh(hamiltonian.real)[0][0]
        classical_time = time.time() - start
        return {
            "quantum_time": quantum_time,
            "classical_time": classical_time,
            "quantum_energy": float(result["energy"]),
            "exact_energy": float(exact),
            "approximation_ratio": float(result["energy"] / exact) if exact != 0 else 0.0,
        }

    def benchmark_qml(self, X: np.ndarray, y: np.ndarray) -> Dict:
        import time
        qml = QuantumMachineLearning(min(4, X.shape[1]))
        start = time.time()
        qml.train(X, y, epochs=30, lr=0.02)
        quantum_time = time.time() - start
        start = time.time()
        from sklearn.linear_model import LogisticRegression
        clf = LogisticRegression(max_iter=100)
        clf.fit(X, y)
        classical_preds = clf.predict(X)
        classical_time = time.time() - start
        quantum_preds = qml.predict(X)
        return {
            "quantum_time": quantum_time,
            "classical_time": classical_time,
            "quantum_accuracy": float(np.mean(quantum_preds == y)),
            "classical_accuracy": float(np.mean(classical_preds == y)),
        }

    def benchmark_amplitude_estimation(self, num_qubits: int = 4) -> Dict:
        from .amplitude_estimation import QuantumAmplitudeEstimation
        qae = QuantumAmplitudeEstimation(num_qubits)
        sim = QuantumCircuitSimulator(num_qubits)
        for i in range(num_qubits):
            sim.ry(i, np.pi / 4)
        probs = sim.get_probabilities()
        target_prob = sum(v for k, v in probs.items() if k.count("1") >= num_qubits // 2)
        result = qae.estimate(target_prob, num_qubits)
        return {
            "estimated": result["estimate"],
            "exact": target_prob,
            "error": abs(result["estimate"] - target_prob),
            "qubits_used": num_qubits,
        }

    def run_all(self, X: np.ndarray, y: np.ndarray) -> List[BenchmarkResult]:
        results = []
        qaoa_result = self.benchmark_qaoa()
        results.append(BenchmarkResult(
            name="QAOA",
            quantum_time=qaoa_result["quantum_time"],
            classical_time=qaoa_result["classical_time"],
            quantum_accuracy=qaoa_result["approximation_ratio"],
            classical_accuracy=1.0,
            speedup=qaoa_result["classical_time"] / max(qaoa_result["quantum_time"], 1e-6),
            advantage=qaoa_result["approximation_ratio"],
        ))
        qml_result = self.benchmark_qml(X, y)
        results.append(BenchmarkResult(
            name="QML",
            quantum_time=qml_result["quantum_time"],
            classical_time=qml_result["classical_time"],
            quantum_accuracy=qml_result["quantum_accuracy"],
            classical_accuracy=qml_result["classical_accuracy"],
            speedup=qml_result["classical_time"] / max(qml_result["quantum_time"], 1e-6),
            advantage=qml_result["quantum_accuracy"] - qml_result["classical_accuracy"],
        ))
        self.results = results
        return results

    def summary(self) -> Dict:
        if not self.results:
            return {"message": "No benchmarks run"}
        return {
            "num_benchmarks": len(self.results),
            "avg_speedup": float(np.mean([r.speedup for r in self.results])),
            "avg_advantage": float(np.mean([r.advantage for r in self.results])),
            "results": [
                {
                    "name": r.name,
                    "speedup": r.speedup,
                    "advantage": r.advantage,
                    "quantum_accuracy": r.quantum_accuracy,
                    "classical_accuracy": r.classical_accuracy,
                }
                for r in self.results
            ],
        }
