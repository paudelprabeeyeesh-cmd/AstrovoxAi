import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator

@dataclass
class CountingResult:
    estimated_count: int
    exact_count: int
    error: float
    num_qubits: int

class QuantumApproximateCounting:
    def __init__(self, num_qubits: int = 6):
        self.num_qubits = num_qubits

    def count(self, oracle: Callable[[int], bool], num_items: int) -> CountingResult:
        sim = QuantumCircuitSimulator(self.num_qubits)
        for i in range(self.num_qubits):
            sim.h(i)
        for item in range(num_items):
            if oracle(item):
                sim.x(0)
        for i in range(self.num_qubits - 1):
            sim.cnot(i, i + 1)
        for i in range(self.num_qubits):
            sim.h(i)
        result = sim.run(shots=1024)
        measured = [int(k, 2) for k in result.counts.keys() for _ in range(result.counts[k])]
        theta = np.mean(measured) / (2 ** self.num_qubits) * 2 * np.pi
        estimated = int(num_items * np.sin(theta) ** 2) if theta > 0 else 0
        return CountingResult(estimated_count=max(0, estimated), exact_count=sum(1 for i in range(num_items) if oracle(i)), error=0.0, num_qubits=self.num_qubits)

    def approximate_count(self, oracle: Callable[[int], bool], universe_size: int) -> Dict:
        results = []
        for num_bits in range(2, self.num_qubits + 1):
            sim = QuantumCircuitSimulator(num_bits)
            for i in range(num_bits):
                sim.h(i)
            marked = sum(1 for i in range(min(2 ** num_bits, universe_size)) if oracle(i))
            for i in range(num_bits - 1):
                sim.cnot(i, i + 1)
            for i in range(num_bits):
                sim.h(i)
            result = sim.run(shots=512)
            measured = [int(k, 2) for k in result.counts.keys()]
            avg_measured = np.mean(measured)
            theta = avg_measured / (2 ** num_bits) * 2 * np.pi
            est = int(2 ** num_bits * np.sin(theta) ** 2) if theta > 0 else 0
            results.append({"num_bits": num_bits, "estimated": est, "exact": marked})
        return {"results": results, "best_estimate": max(results, key=lambda r: r["num_bits"])["estimated"] if results else 0}

    def threshold_count(self, values: List[float], threshold: float) -> int:
        oracle = lambda i: i < len(values) and values[i] >= threshold
        return sum(1 for i in range(len(values)) if oracle(i))

    def quantum_counter(self, n: int, k: int) -> int:
        sim = QuantumCircuitSimulator(n)
        for i in range(n):
            sim.h(i)
        for i in range(n - k):
            sim.cnot(i, n - 1)
        for i in range(n):
            sim.h(i)
        result = sim.run(shots=1024)
        counts = [int(k, 2) for k in result.counts.keys() for _ in range(result.counts[k])]
        return int(np.median(counts))
