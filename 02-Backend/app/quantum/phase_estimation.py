import numpy as np
from typing import Callable, Optional, Dict
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator

@dataclass
class PhaseEstimationResult:
    estimated_phase: float
    exact_phase: Optional[float]
    binary_estimate: str
    num_qubits: int

class QuantumPhaseEstimation:
    def __init__(self, num_qubits: int = 4):
        self.num_qubits = num_qubits

    def estimate(self, unitary: Callable[[int], QuantumCircuitSimulator], eigenstate_prep: Optional[Callable] = None) -> PhaseEstimationResult:
        sim = QuantumCircuitSimulator(self.num_qubits + 1)
        for i in range(self.num_qubits):
            sim.h(i)
        if eigenstate_prep:
            eigenstate_prep(sim)
        for control in range(self.num_qubits):
            for _ in range(2 ** control):
                u = unitary(control)
                sim.cnot(control, self.num_qubits)
        for i in range(self.num_qubits):
            sim.h(i)
            if i > 0:
                for j in range(i):
                    sim.phase(j, -np.pi / (2 ** (i - j)))
        result = sim.run(shots=1024)
        most_likely = max(result.counts, key=result.counts.get)
        phase = int(most_likely[:self.num_qubits], 2) / (2 ** self.num_qubits)
        return PhaseEstimationResult(
            estimated_phase=phase,
            exact_phase=None,
            binary_estimate=most_likely[:self.num_qubits],
            num_qubits=self.num_qubits,
        )

    def estimate_unitary_phase(self, phase: float) -> Dict:
        def unitary_fn(control: int) -> QuantumCircuitSimulator:
            sim = QuantumCircuitSimulator(1)
            sim.rz(0, 2 * np.pi * phase)
            return sim
        def prep(sim: QuantumCircuitSimulator) -> None:
            sim.x(self.num_qubits)
        result = self.estimate(unitary_fn, prep)
        return {
            "estimated": result.estimated_phase,
            "exact": phase,
            "error": abs(result.estimated_phase - phase),
            "binary": result.binary_estimate,
        }

    def quantum_fourier_transform(self, state: np.ndarray) -> np.ndarray:
        n = int(np.log2(len(state)))
        result = np.zeros(len(state), dtype=np.complex128)
        for k in range(len(state)):
            for j in range(len(state)):
                result[k] += state[j] * np.exp(2j * np.pi * j * k / len(state)) / np.sqrt(len(state))
        return result

    def inverse_qft(self, state: np.ndarray) -> np.ndarray:
        n = len(state)
        result = np.zeros(n, dtype=np.complex128)
        for k in range(n):
            for j in range(n):
                result[k] += state[j] * np.exp(-2j * np.pi * j * k / n) / np.sqrt(n)
        return result

    def shor_period_finding(self, a: int, N: int, num_qubits: int = 4) -> Optional[int]:
        def unitary_fn(control: int) -> QuantumCircuitSimulator:
            sim = QuantumCircuitSimulator(1)
            sim.rz(0, 2 * np.pi * (a ** (2 ** control) % N) / N)
            return sim
        result = self.estimate(unitary_fn)
        phase = result.estimated_phase
        if phase == 0:
            return None
        frac = self._continued_fractions(phase, N)
        return frac

    def _continued_fractions(self, x: float, max_denominator: int) -> int:
        a = int(np.floor(x))
        if a == 0:
            return 1
        frac = x - a
        for d in range(2, max_denominator + 1):
            if abs(frac - round(frac * d) / d) < 1e-6:
                return d
        return a

    def hamiltonian_evolution_phase(self, hamiltonian: np.ndarray, time: float, num_qubits: int = 4) -> float:
        sim = QuantumCircuitSimulator(num_qubits)
        for i in range(num_qubits):
            sim.ry(i, time * np.pi / (i + 1))
        probs = sim.get_probabilities()
        phase = sum(int(k, 2) * p for k, p in probs.items()) / (2 ** num_qubits)
        return float(phase)
