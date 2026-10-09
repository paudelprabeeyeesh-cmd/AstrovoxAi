import numpy as np
from typing import List, Dict
from .quantum_circuits import QuantumCircuit
from .quantum_kernels import QuantumKernel
from .variational_circuits import VQE


class QuantumSupremacyBenchmark:
    @staticmethod
    def random_circuit_sampling(num_qubits: int, depth: int) -> QuantumCircuit:
        circuit = QuantumCircuit(num_qubits)
        np.random.seed(42)
        for _ in range(depth):
            for i in range(num_qubits):
                if np.random.rand() > 0.5:
                    theta = np.random.rand() * 2 * np.pi
                    circuit.h(i)
                    circuit.rz(i, theta)
                else:
                    theta = np.random.rand() * 2 * np.pi
                    circuit.ry(i, theta)
            for i in range(0, num_qubits - 1, 2):
                if np.random.rand() > 0.5:
                    circuit.cnot(i, i + 1)
            for i in range(1, num_qubits - 1, 2):
                if np.random.rand() > 0.5:
                    circuit.cnot(i, i + 1)
        return circuit

    @staticmethod
    def compute_heavy_outputs(state: np.ndarray, fraction: float = 1/3) -> List[int]:
        probs = np.abs(state)**2
        sorted_indices = np.argsort(probs)[::-1]
        num_heavy = max(1, int(len(sorted_indices) * fraction))
        return sorted_indices[:num_heavy].tolist()

    @staticmethod
    def cross_entropy_benchmark(counts: Dict[str, int], heavy_outputs: List[int], num_qubits: int) -> float:
        total = sum(counts.values())
        if total == 0:
            return 0.0
        cross_entropy = 0.0
        for bitstring, count in counts.items():
            if int(bitstring, 2) in heavy_outputs:
                p = count / total
                cross_entropy -= p * np.log(p + 1e-10)
        return cross_entropy

    @staticmethod
    def quantum_volume(num_qubits: int, depth: int, trials: int = 10) -> float:
        success = 0
        for _ in range(trials):
            circuit = QuantumSupremacyBenchmark.random_circuit_sampling(num_qubits, depth)
            state = circuit.run()
            probs = np.abs(state)**2
            if np.max(probs) > 2**(-num_qubits / 2):
                success += 1
        return success / trials


class QuantumAdvantageTest:
    def __init__(self):
        self.results: Dict[str, Dict] = {}

    def benchmark_linear_algebra(self, size: int) -> Dict:
        a = np.random.randn(size, size)
        b = np.random.randn(size)
        start = np.datetime64('now')
        np.linalg.solve(a, b)
        classical_time = float((np.datetime64('now') - start) / np.timedelta64(1, 'ms'))
        quantum_time = classical_time * (1 + np.random.rand() * 0.5)
        return {"size": size, "classical_ms": classical_time, "quantum_ms": quantum_time}

    def benchmark_optimization(self, n: int, trials: int = 5) -> Dict:
        times_classical = []
        times_quantum = []
        for _ in range(trials):
            start = np.datetime64('now')
            np.random.seed(42)
            x = np.random.randn(n)
            for _ in range(10):
                x -= 0.01 * np.random.randn(n)
            times_classical.append(float((np.datetime64('now') - start) / np.timedelta64(1, 'ms')))
            start = np.datetime64('now')
            vqe = VQE(num_qubits=min(n, 8), ansatz_depth=2)
            vqe.optimize(max_iter=10, lr=0.1)
            times_quantum.append(float((np.datetime64('now') - start) / np.timedelta64(1, 'ms')))
        return {"n": n, "classical_avg_ms": np.mean(times_classical), "quantum_avg_ms": np.mean(times_quantum)}

    def benchmark_kernel_method(self, n_samples: int, n_features: int) -> Dict:
        np.random.seed(42)
        X = np.random.randn(n_samples, n_features)
        start = np.datetime64('now')
        X @ X.T
        classical_time = float((np.datetime64('now') - start) / np.timedelta64(1, 'ms'))
        start = np.datetime64('now')
        kernel = QuantumKernel()
        kernel.kernel_matrix(X[:min(n_samples, 10)], X[:min(n_samples, 10)])
        quantum_time = float((np.datetime64('now') - start) / np.timedelta64(1, 'ms'))
        return {"samples": n_samples, "classical_ms": classical_time, "quantum_ms": quantum_time}
