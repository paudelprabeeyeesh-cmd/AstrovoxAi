import numpy as np
from typing import Callable, Dict, Optional
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator

@dataclass
class AmplitudeEstimationResult:
    estimate: float
    exact: Optional[float]
    num_qubits: int
    confidence_interval: tuple

class QuantumAmplitudeEstimation:
    def __init__(self, num_qubits: int = 4):
        self.num_qubits = num_qubits

    def _grover_oracle(self, sim: QuantumCircuitSimulator, target_amplitude: float) -> None:
        for i in range(sim.num_qubits):
            sim.h(i)
        sim.toffoli(0, 1, 2) if sim.num_qubits >= 3 else None

    def _grover_diffusion(self, sim: QuantumCircuitSimulator) -> None:
        for i in range(sim.num_qubits):
            sim.h(i)
            sim.x(i)
        sim.toffoli(0, 1, 2) if sim.num_qubits >= 3 else None
        for i in range(sim.num_qubits):
            sim.x(i)
            sim.h(i)

    def estimate(self, target_probability: float, num_qubits: Optional[int] = None) -> Dict:
        n = num_qubits or self.num_qubits
        sim = QuantumCircuitSimulator(n)
        for i in range(n):
            sim.h(i)
        for i in range(n):
            sim.ry(i, 2 * np.arcsin(np.sqrt(target_probability)))
        optimal_iterations = int(np.pi / 4 * np.sqrt(1 / max(target_probability, 1e-10)))
        for _ in range(optimal_iterations):
            self._grover_oracle(sim, target_probability)
            self._grover_diffusion(sim)
        result = sim.run(shots=1024)
        probs = result.probabilities
        estimated = sum(int(k, 2) / (2 ** n) * p for k, p in probs.items())
        return {
            "estimate": float(estimated),
            "exact": target_probability,
            "num_qubits": n,
            "iterations": optimal_iterations,
            "confidence_interval": (max(0.0, estimated - 0.05), min(1.0, estimated + 0.05)),
        }

    def quantum_integration(self, f: Callable[[float], float], a: float, b: float, num_qubits: int = 4) -> float:
        sim = QuantumCircuitSimulator(num_qubits)
        for i in range(num_qubits):
            sim.h(i)
        for i in range(num_qubits):
            x = a + (b - a) * (i + 0.5) / num_qubits
            sim.ry(i, f(x) * np.pi / 2)
        probs = sim.get_probabilities()
        integral = sum(f(a + (b - a) * int(k, 2) / (2 ** num_qubits)) * p for k, p in probs.items())
        return float(integral * (b - a) / (2 ** num_qubits))

    def amplitude_amplification(self, amplitude: float, iterations: int) -> float:
        theta = np.arcsin(np.sqrt(amplitude))
        new_theta = (2 * iterations + 1) * theta
        return float(np.sin(new_theta) ** 2)

    def monte_carlo_quantum(self, payoff_fn: Callable[[float], float], num_paths: int, num_qubits: int = 4) -> Dict:
        sim = QuantumCircuitSimulator(num_qubits)
        for i in range(num_qubits):
            sim.h(i)
        for i in range(num_qubits):
            sim.rz(i, np.random.uniform(0, 2 * np.pi))
        probs = sim.get_probabilities()
        payoffs = [payoff_fn(int(k, 2) / (2 ** num_qubits)) for k in probs]
        weighted_sum = sum(p * po for p, po in zip(probs.values(), payoffs))
        return {
            "estimated_price": float(weighted_sum),
            "num_qubits": num_qubits,
            "variance": float(np.var(payoffs)),
        }
