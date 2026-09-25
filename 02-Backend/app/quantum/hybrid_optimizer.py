import numpy as np
from typing import List, Tuple, Dict, Callable, Optional
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator
from .qml_algorithms import QuantumMachineLearning
from .qaoa import QAOA
from .qrandom import QuantumRandomNumberGenerator
from .vqc import VariationalQuantumCircuit
from .hybrid_workflows import HybridQuantumWorkflow

@dataclass
class OptimizationResult:
    best_x: np.ndarray
    best_f: float
    iterations: int
    history: List[Dict]
    method: str

class HybridQuantumOptimizer:
    def __init__(self, num_qubits: int = 6, seed: Optional[int] = None):
        self.num_qubits = num_qubits
        self.qrng = QuantumRandomNumberGenerator(num_qubits, seed=seed)
        self.qml = QuantumMachineLearning(num_qubits)
        self.hybrid = HybridQuantumWorkflow(num_qubits)

    def optimize(self, objective: Callable[[np.ndarray], float], bounds: List[Tuple[float, float]], method: str = "quantum", max_iter: int = 100) -> OptimizationResult:
        if method == "quantum":
            return self._quantum_optimize(objective, bounds, max_iter)
        elif method == "hybrid":
            return self._hybrid_optimize(objective, bounds, max_iter)
        elif method == "qaoa":
            return self._qaoa_optimize(objective, bounds, max_iter)
        else:
            return self._classical_optimize(objective, bounds, max_iter)

    def _quantum_optimize(self, objective: Callable, bounds: List[Tuple[float, float]], max_iter: int) -> OptimizationResult:
        best_x = None
        best_f = float("inf")
        history = []
        for i in range(max_iter):
            rand_vals = self.qrng.generate_uniform(len(bounds))
            x = np.array([low + rand_vals[j] * (high - low) for j, (low, high) in enumerate(bounds)])
            sim = QuantumCircuitSimulator(self.num_qubits)
            for j, val in enumerate(x):
                sim.ry(j, val * np.pi / (bounds[j][1] - bounds[j][0]))
            f_val = objective(x)
            if f_val < best_f:
                best_f = f_val
                best_x = x
            history.append({"iteration": i, "x": x.tolist(), "f": f_val})
        return OptimizationResult(best_x=best_x, best_f=best_f, iterations=max_iter, history=history, method="quantum")

    def _hybrid_optimize(self, objective: Callable, bounds: List[Tuple[float, float]], max_iter: int) -> OptimizationResult:
        best_x = None
        best_f = float("inf")
        history = []
        for i in range(max_iter):
            if i % 2 == 0:
                rand_vals = self.qrng.generate_uniform(len(bounds))
                x = np.array([low + rand_vals[j] * (high - low) for j, (low, high) in enumerate(bounds)])
            else:
                if best_x is not None:
                    noise = np.random.randn(len(bounds)) * 0.1
                    x = np.clip(best_x + noise, [b[0] for b in bounds], [b[1] for b in bounds])
                else:
                    rand_vals = self.qrng.generate_uniform(len(bounds))
                    x = np.array([low + rand_vals[j] * (high - low) for j, (low, high) in enumerate(bounds)])
            f_val = objective(x)
            if f_val < best_f:
                best_f = f_val
                best_x = x
            history.append({"iteration": i, "x": x.tolist(), "f": f_val})
        return OptimizationResult(best_x=best_x, best_f=best_f, iterations=max_iter, history=history, method="hybrid")

    def _qaoa_optimize(self, objective: Callable, bounds: List[Tuple[float, float]], max_iter: int) -> OptimizationResult:
        n = min(len(bounds), self.num_qubits)
        qaoa = QAOA(n)
        grid = [np.linspace(low, high, 2 ** n) for low, high in bounds]
        H = np.zeros((2 ** n, 2 ** n))
        for state in range(2 ** n):
            x = np.array([grid[j][(state >> j) & 1] for j in range(n)])
            H[state, state] = objective(x)
        edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
        result = qaoa.solve(H, edges, depth=2, max_iterations=max_iter // 10)
        best_state = max(range(2 ** n), key=lambda s: -H[s, s])
        best_x = np.array([grid[j][(best_state >> j) & 1] for j in range(n)])
        history = [{"iteration": i, "energy": H[i, i]} for i in range(min(max_iter, 2 ** n))]
        return OptimizationResult(best_x=best_x, best_f=float(H[best_state, best_state]), iterations=max_iter, history=history, method="qaoa")

    def _classical_optimize(self, objective: Callable, bounds: List[Tuple[float, float]], max_iter: int) -> OptimizationResult:
        best_x = np.random.uniform([b[0] for b in bounds], [b[1] for b in bounds])
        best_f = objective(best_x)
        history = []
        for i in range(max_iter):
            x = np.random.uniform([b[0] for b in bounds], [b[1] for b in bounds])
            f_val = objective(x)
            if f_val < best_f:
                best_f = f_val
                best_x = x
            history.append({"iteration": i, "x": x.tolist(), "f": f_val})
        return OptimizationResult(best_x=best_x, best_f=best_f, iterations=max_iter, history=history, method="classical")

    def optimize_with_vqc(self, objective: Callable, bounds: List[Tuple[float, float]], epochs: int = 50) -> OptimizationResult:
        dim = len(bounds)
        vqc = VariationalQuantumCircuit(min(dim, 4))
        best_x = None
        best_f = float("inf")
        history = []
        for epoch in range(epochs):
            x = np.random.uniform([b[0] for b in bounds], [b[1] for b in bounds])
            sim = vqc._build_circuit(vqc.params, x)
            probs = sim.get_probabilities()
            pred = sum(int(k, 2) * p for k, p in probs.items())
            f_val = objective(x)
            if f_val < best_f:
                best_f = f_val
                best_x = x
            vqc.train(np.array([x]), np.array([f_val]), epochs=1, lr=0.01)
            history.append({"iteration": epoch, "x": x.tolist(), "f": f_val})
        return OptimizationResult(best_x=best_x, best_f=best_f, iterations=epochs, history=history, method="vqc")

    def bayesian_quantum_optimization(self, objective: Callable, bounds: List[Tuple[float, float]], n_init: int = 5, n_iter: int = 20) -> OptimizationResult:
        X_init = np.random.uniform([b[0] for b in bounds], [b[1] for b in bounds], size=(n_init, len(bounds)))
        y_init = np.array([objective(x) for x in X_init])
        X = X_init.copy()
        y = y_init.copy()
        history = []
        for i in range(n_init):
            history.append({"iteration": i, "x": X[i].tolist(), "f": float(y[i]), "type": "init"})
        for i in range(n_iter):
            idx = np.argmin(y)
            x_best = X[idx]
            sim = QuantumCircuitSimulator(min(len(bounds), 4))
            for j, val in enumerate(x_best):
                sim.ry(j, val * np.pi / (bounds[j][1] - bounds[j][0]))
            rand_vals = self.qrng.generate_uniform(len(bounds))
            x_new = np.clip(x_best + 0.1 * rand_vals, [b[0] for b in bounds], [b[1] for b in bounds])
            y_new = objective(x_new)
            X = np.vstack([X, x_new])
            y = np.append(y, y_new)
            history.append({"iteration": n_init + i, "x": x_new.tolist(), "f": float(y_new), "type": "quantum_proposal"})
        best_idx = np.argmin(y)
        return OptimizationResult(best_x=X[best_idx], best_f=float(y[best_idx]), iterations=n_init + n_iter, history=history, method="bayesian_quantum")
