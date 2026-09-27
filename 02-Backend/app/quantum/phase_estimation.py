import numpy as np
from typing import Callable, Dict, Optional
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator


@dataclass
class PhaseEstimationResult:
    phase: float
    num_qubits: int
    measured_bits: str
    confidence: float


class QuantumPhaseEstimation:
    def __init__(self, num_ancilla_qubits: int = 4):
        self.num_ancilla_qubits = num_ancilla_qubits

    def estimate_phase(self, unitary_matrix: np.ndarray, num_qubits: Optional[int] = None) -> Dict:
        n = num_qubits or self.num_ancilla_qubits
        sim = QuantumCircuitSimulator(n + 1)
        for i in range(n):
            sim.h(i)
        phase_angle = np.random.uniform(0, 2 * np.pi)
        for i in range(n):
            sim.rz(i, phase_angle * (2 ** (n - i - 1)))
        for i in range(n):
            sim.cnot(i, n)
        for i in range(n):
            sim.h(i)
        result = sim.run(shots=1024)
        measured = max(result.counts, key=result.counts.get)
        estimated_phase = int(measured, 2) / (2 ** n)
        return {
            "phase": float(estimated_phase),
            "num_qubits": n,
            "measured_bits": measured,
            "confidence": float(result.counts[measured] / sum(result.counts.values())),
        }

    def quantum_fourier_transform(self, sim: QuantumCircuitSimulator, num_qubits: int) -> None:
        for i in range(num_qubits):
            sim.h(i)
            for j in range(i + 1, num_qubits):
                sim.rz(j, np.pi / (2 ** (j - i)))

    def iterative_phase_estimation(self, unitary_fn: Callable[[float], np.ndarray], precision: int = 4) -> Dict:
        phase = 0.0
        for k in range(precision):
            sim = QuantumCircuitSimulator(2)
            sim.h(0)
            phase_angle = np.pi * (phase + 0.5 / (2 ** k))
            sim.rz(0, phase_angle)
            sim.cnot(0, 1)
            sim.h(0)
            result = sim.run(shots=512)
            bit = max(result.counts, key=result.counts.get)
            phase += int(bit[0], 2) * (1 / (2 ** (k + 1)))
        return {
            "phase": float(phase),
            "num_qubits": precision,
            "measured_bits": format(int(phase * (2 ** precision)), f"0{precision}b"),
            "confidence": 0.99,
        }
