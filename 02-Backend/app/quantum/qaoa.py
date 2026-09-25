import numpy as np
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator

class QAOA:
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.params: Optional[np.ndarray] = None

    def _maxcut_hamiltonian(self, edges: List[Tuple[int, int]], weights: Optional[List[float]] = None) -> np.ndarray:
        dim = 2 ** self.num_qubits
        H = np.zeros((dim, dim))
        if weights is None:
            weights = [1.0] * len(edges)
        for (u, v), w in zip(edges, weights):
            for state in range(dim):
                bit_u = (state >> (self.num_qubits - u - 1)) & 1
                bit_v = (state >> (self.num_qubits - v - 1)) & 1
                if bit_u != bit_v:
                    H[state, state] += w
        return H

    def _build_qaoa_circuit(self, params: np.ndarray, hamiltonian: np.ndarray, edges: List[Tuple[int, int]], depth: int) -> QuantumCircuitSimulator:
        sim = QuantumCircuitSimulator(self.num_qubits)
        for i in range(self.num_qubits):
            sim.h(i)
        for d in range(depth):
            gamma = params[d]
            beta = params[depth + d]
            for (u, v) in edges:
                sim.cnot(u, v)
                sim.rz(v, 2 * gamma)
                sim.cnot(u, v)
            for i in range(self.num_qubits):
                sim.rx(i, 2 * beta)
        return sim

    def solve(self, hamiltonian: np.ndarray, edges: List[Tuple[int, int]], depth: int = 2, max_iterations: int = 50, lr: float = 0.1) -> Dict:
        params = np.random.randn(2 * depth) * 0.1
        best_energy = float("inf")
        best_params = params.copy()
        for iteration in range(max_iterations):
            grads = np.zeros_like(params)
            energy = 0.0
            for d in range(2 * depth):
                eps = 1e-5
                params_plus = params.copy()
                params_plus[d] += eps
                params_minus = params.copy()
                params_minus[d] -= eps
                e_plus = self._cost_function(params_plus, hamiltonian, edges, depth)
                e_minus = self._cost_function(params_minus, hamiltonian, edges, depth)
                grads[d] = (e_plus - e_minus) / (2 * eps)
            energy = self._cost_function(params, hamiltonian, edges, depth)
            params -= lr * grads
            if energy < best_energy:
                best_energy = energy
                best_params = params.copy()
        return {"energy": best_energy, "params": best_params, "iterations": max_iterations}

    def _cost_function(self, params: np.ndarray, hamiltonian: np.ndarray, edges: List[Tuple[int, int]], depth: int) -> float:
        sim = self._build_qaoa_circuit(params, hamiltonian, edges, depth)
        return sim.expectation(hamiltonian)

    def maxcut(self, edges: List[Tuple[int, int]], weights: Optional[List[float]] = None, depth: int = 2) -> Dict:
        H = self._maxcut_hamiltonian(edges, weights)
        result = self.solve(H, edges, depth=depth)
        sim = self._build_qaoa_circuit(result["params"], H, edges, depth)
        probs = sim.get_probabilities()
        best_state = max(probs, key=probs.get)
        cut_value = sum(w for i, (u, v) in enumerate(edges) if best_state[u] != best_state[v] for w in [weights[i] if weights else 1.0])
        return {
            "best_state": best_state,
            "cut_value": float(cut_value),
            "energy": result["energy"],
            "probability": probs[best_state],
        }

    def tsp(self, distances: np.ndarray, depth: int = 2) -> Dict:
        n = len(distances)
        num_qubits = n * n
        qaoa = QAOA(num_qubits)
        H = np.zeros((2 ** num_qubits, 2 ** num_qubits))
        for state in range(2 ** num_qubits):
            bits = format(state, f"0{num_qubits}b")
            for i in range(n):
                city_qubits = [i * n + j for j in range(n)]
                if sum(int(bits[q]) for q in city_qubits) != 1:
                    H[state, state] += 1000
            for i in range(n):
                for j in range(i + 1, n):
                    if sum(int(bits[i * n + k]) for k in range(n)) == 1 and sum(int(bits[j * n + k]) for k in range(n)) == 1:
                        for k in range(n):
                            if int(bits[i * n + k]) and int(bits[j * n + (k + 1) % n]):
                                H[state, state] += distances[i, j]
        result = qaoa.solve(H, [(i, j) for i in range(n) for j in range(i + 1, n)][:n], depth=depth)
        return {"energy": result["energy"], "params": result["params"]}

    def portfolio_optimization(self, returns: np.ndarray, covariance: np.ndarray, risk_aversion: float = 0.5, depth: int = 2) -> Dict:
        n = len(returns)
        H = np.zeros((2 ** n, 2 ** n))
        for state in range(2 ** n):
            bits = format(state, f"0{n}b")
            selected = [i for i, b in enumerate(bits) if b == "1"]
            if not selected:
                H[state, state] = 1000
                continue
            ret = sum(returns[i] for i in selected)
            var = sum(covariance[i, j] for i in selected for j in selected)
            H[state, state] = -ret + risk_aversion * var
        edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
        result = self.solve(H, edges[:min(n, len(edges))], depth=depth)
        return {"energy": result["energy"], "params": result["params"]}
