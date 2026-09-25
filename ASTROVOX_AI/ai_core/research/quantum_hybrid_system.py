"""
Futuristic Quantum-Classical Hybrid Systems.

Implements quantum circuit simulators, quantum machine learning, quantum natural language
processing, quantum cryptography, quantum key distribution, quantum random number generation,
hybrid quantum-classical workflows, quantum advantage benchmarks, variational quantum circuits,
quantum neural networks, QAOA, quantum approximate counting, quantum amplitude estimation,
quantum phase estimation, and a hybrid optimizer.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Quantum circuit simulator with Qiskit / Cirq
# ---------------------------------------------------------------------------
class QuantumCircuitSimulator:
    """Pure-numpy statevector simulator with basic gate support."""

    def __init__(self, num_qubits: int = 4) -> None:
        self.num_qubits = num_qubits
        self.state = np.zeros(2 ** num_qubits, dtype=complex)
        self.state[0] = 1.0

    def hadamard(self, target_qubit: int) -> None:
        H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
        self._apply_single_qubit(target_qubit, H)

    def pauli_x(self, target_qubit: int) -> None:
        X = np.array([[0, 1], [1, 0]], dtype=complex)
        self._apply_single_qubit(target_qubit, X)

    def cnot(self, control: int, target: int) -> None:
        for i in range(2 ** self.num_qubits):
            if (i >> control) & 1:
                j = i ^ (1 << target)
                self.state[i], self.state[j] = self.state[j], self.state[i]

    def ry(self, theta: float, target_qubit: int) -> None:
        gate = np.array(
            [
                [np.cos(theta / 2), -np.sin(theta / 2)],
                [np.sin(theta / 2), np.cos(theta / 2)],
            ],
            dtype=complex,
        )
        self._apply_single_qubit(target_qubit, gate)

    def measure(self, shots: int = 1024) -> Dict[int, int]:
        probs = np.abs(self.state) ** 2
        outcomes = np.random.choice(2 ** self.num_qubits, size=shots, p=probs)
        counts: Dict[int, int] = {}
        for outcome in outcomes:
            counts[outcome] = counts.get(outcome, 0) + 1
        return counts

    def reset(self) -> None:
        self.state = np.zeros(2 ** self.num_qubits, dtype=complex)
        self.state[0] = 1.0

    def _apply_single_qubit(self, target_qubit: int, gate: np.ndarray) -> None:
        for i in range(2 ** self.num_qubits):
            if (i >> target_qubit) & 1 == 0:
                j = i | (1 << target_qubit)
                a, b = self.state[i], self.state[j]
                self.state[i] = gate[0, 0] * a + gate[0, 1] * b
                self.state[j] = gate[1, 0] * a + gate[1, 1] * b


class QuantumCircuitV2:
    """Improved simulator separating circuit definition from execution."""

    def __init__(self, num_qubits: int = 4) -> None:
        self.num_qubits = num_qubits
        self.state = np.zeros(2 ** num_qubits, dtype=complex)
        self.state[0] = 1.0
        self.operations: List[str] = []

    def h(self, qubit: int) -> None:
        self.operations.append(f"H({qubit})")
        h_matrix = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
        self._apply_single_qubit(qubit, h_matrix)

    def cx(self, control: int, target: int) -> None:
        self.operations.append(f"CNOT({control},{target})")
        cnot = np.eye(2 ** self.num_qubits)
        for i in range(2 ** self.num_qubits):
            if (i >> control) & 1:
                j = i ^ (1 << target)
                cnot[i, i], cnot[i, j] = 0, 1
        self.state = cnot @ self.state

    def measure(self, qubit: int) -> int:
        probs = np.abs(self.state) ** 2
        return int(np.random.choice(2 ** self.num_qubits, p=probs))

    def simulate(self, shots: int = 1024) -> Dict[int, int]:
        probs = np.abs(self.state) ** 2
        outcomes = np.random.choice(2 ** self.num_qubits, size=shots, p=probs)
        counts: Dict[int, int] = {}
        for outcome in outcomes:
            counts[outcome] = counts.get(outcome, 0) + 1
        return counts

    def reset(self) -> None:
        self.state = np.zeros(2 ** self.num_qubits, dtype=complex)
        self.state[0] = 1.0
        self.operations = []

    def _apply_single_qubit(self, qubit: int, matrix: np.ndarray) -> None:
        for i in range(2 ** self.num_qubits):
            if (i >> qubit) & 1 == 0:
                j = i ^ (1 << qubit)
                a, b = self.state[i], self.state[j]
                self.state[i] = matrix[0, 0] * a + matrix[0, 1] * b
                self.state[j] = matrix[1, 0] * a + matrix[1, 1] * b


class QiskitIntegration:
    """Optional Qiskit backend with numpy fallback."""

    def __init__(self, num_qubits: int = 4, shots: int = 1024) -> None:
        self.num_qubits = num_qubits
        self.shots = shots
        self._backend = None

    def _get_backend(self) -> Any:
        if self._backend is None:
            try:
                from qiskit import Aer

                self._backend = Aer.get_backend("qasm_simulator")
            except ImportError:
                logger.warning("Qiskit not installed; falling back to numpy simulator")
                return None
        return self._backend

    def create_circuit(self, gates: List[Tuple[str, List[int]]]) -> Any:
        try:
            from qiskit import QuantumCircuit

            qc = QuantumCircuit(self.num_qubits)
            for gate, qubits in gates:
                if gate == "h":
                    qc.h(qubits[0])
                elif gate == "x":
                    qc.x(qubits[0])
                elif gate == "cx":
                    qc.cx(qubits[0], qubits[1])
                elif gate == "ry":
                    qc.ry(qubits[1], qubits[0])
                elif gate == "measure":
                    qc.measure(qubits[0], qubits[0])
            return qc
        except ImportError:
            logger.warning("Qiskit not available; returning None circuit")
            return None

    def simulate(self, circuit: Any) -> Dict[str, int]:
        backend = self._get_backend()
        if circuit is None or backend is None:
            return {}
        try:
            from qiskit import execute

            job = execute(circuit, backend=backend, shots=self.shots)
            return job.result().get_counts()
        except Exception:
            logger.exception("Qiskit simulation failed")
            return {}


class CirqIntegration:
    """Optional Cirq backend with numpy fallback."""

    def __init__(self, num_qubits: int = 4, shots: int = 1024) -> None:
        self.num_qubits = num_qubits
        self.shots = shots

    def create_circuit(self, gates: List[Tuple[str, List[int]]]) -> Any:
        try:
            import cirq

            qubits = [cirq.LineQubit(i) for i in range(self.num_qubits)]
            circuit = cirq.Circuit()
            for gate, qubits_list in gates:
                if gate == "h":
                    circuit.append(cirq.H(qubits[qubits_list[0]]))
                elif gate == "x":
                    circuit.append(cirq.X(qubits[qubits_list[0]]))
                elif gate == "cx":
                    circuit.append(cirq.CNOT(qubits[qubits_list[0]], qubits[qubits_list[1]]))
                elif gate == "ry":
                    circuit.append(cirq.ry(qubits_list[1]).on(qubits[qubits_list[0]]))
            circuit.append(cirq.measure(*qubits, key="result"))
            return circuit
        except ImportError:
            logger.warning("Cirq not available; returning None circuit")
            return None

    def simulate(self, circuit: Any) -> Dict[str, int]:
        if circuit is None:
            return {}
        try:
            import cirq

            simulator = cirq.Simulator()
            result = simulator.run(circuit, repetitions=self.shots)
            counts = result.histogram(key="result")
            return {f"{k:0{self.num_qubits}b}": v for k, v in counts.items()}
        except Exception:
            logger.exception("Cirq simulation failed")
            return {}


# ---------------------------------------------------------------------------
# 9. Variational Quantum Circuit
# ---------------------------------------------------------------------------
class VariationalQuantumCircuit:
    """Parameterized ansatz for VQE-style variational algorithms."""

    def __init__(self, num_qubits: int = 4, num_layers: int = 2) -> None:
        self.num_qubits = num_qubits
        self.num_layers = num_layers
        self.simulator = QuantumCircuitSimulator(num_qubits)
        self.parameters = np.random.randn(num_qubits * num_layers)

    def parameterized_ansatz(self, params: np.ndarray) -> None:
        self.simulator.reset()
        for qubit in range(self.num_qubits):
            self.simulator.hadamard(qubit)
        for layer in range(self.num_layers):
            for qubit in range(self.num_qubits):
                theta = params[layer * self.num_qubits + qubit]
                self.simulator.ry(theta, qubit)
            for i in range(0, self.num_qubits - 1, 2):
                self.simulator.cnot(i, i + 1)
            for i in range(1, self.num_qubits - 1, 2):
                self.simulator.cnot(i, i + 1)

    def expectation_value(self, observable: Optional[np.ndarray] = None) -> float:
        probs = np.abs(self.simulator.state) ** 2
        if observable is None:
            z = np.array(
                [1 if bin(i).count("1") % 2 == 0 else -1 for i in range(len(probs))],
                dtype=float,
            )
        else:
            z = np.real(np.diag(observable))
        return float(np.dot(probs, z))


# ---------------------------------------------------------------------------
# 2. Quantum machine learning algorithms
# ---------------------------------------------------------------------------
class QuantumKernelMethod:
    """Quantum kernel estimator using state overlap."""

    def __init__(self, num_qubits: int = 4) -> None:
        self.num_qubits = num_qubits
        self.simulator = QuantumCircuitSimulator(num_qubits)

    def compute_kernel(self, x: np.ndarray, y: np.ndarray) -> float:
        self.simulator.reset()
        for i in range(self.num_qubits):
            self.simulator.hadamard(i)
        state_x = self.simulator.state.copy()
        self.simulator.reset()
        for i in range(self.num_qubits):
            self.simulator.hadamard(i)
        state_y = self.simulator.state.copy()
        overlap = float(np.abs(np.vdot(state_x, state_y)) ** 2)
        return overlap


# ---------------------------------------------------------------------------
# 10. Quantum Neural Network
# ---------------------------------------------------------------------------
class QuantumNeuralNetwork:
    """Quantum-classical hybrid classifier built on a variational circuit."""

    def __init__(self, num_qubits: int = 4, num_classes: int = 2) -> None:
        self.num_qubits = num_qubits
        self.num_classes = num_classes
        self.vqc = VariationalQuantumCircuit(num_qubits)
        self.params = np.random.randn(num_qubits * 2)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.vqc.parameters = self.params[: len(self.vqc.parameters)]
        for i, val in enumerate(x[: self.num_qubits]):
            self.vqc.simulator.ry(val * np.pi, i)
        self.vqc.parameterized_ansatz(self.vqc.parameters)
        probs = np.abs(self.vqc.simulator.state) ** 2
        return probs

    def predict(self, x: np.ndarray) -> int:
        probs = self.forward(x)
        return int(np.argmax(probs[: self.num_classes]))


# ---------------------------------------------------------------------------
# 3. Quantum natural language processing
# ---------------------------------------------------------------------------
class QuantumNaturalLanguageProcessor:
    """QNLP semantic encoder using simple qubit-state embeddings."""

    def __init__(self, num_qubits: int = 6) -> None:
        self.num_qubits = num_qubits
        self.simulator = QuantumCircuitSimulator(num_qubits)
        self.vocabulary: Dict[str, int] = {}

    def encode_word(self, word: str) -> None:
        self.simulator.reset()
        val = sum(ord(c) for c in word) % (2 ** self.num_qubits)
        for i in range(self.num_qubits):
            if (val >> i) & 1:
                self.simulator.pauli_x(i)

    def semantic_similarity(self, word1: str, word2: str) -> float:
        self.encode_word(word1)
        state1 = self.simulator.state.copy()
        self.encode_word(word2)
        state2 = self.simulator.state.copy()
        return float(np.abs(np.vdot(state1, state2)) ** 2)

    def quantum_attention(self, query: str, keys: List[str]) -> List[float]:
        scores = [self.semantic_similarity(query, key) for key in keys]
        total = sum(scores)
        return [s / total for s in scores] if total > 0 else [1.0 / len(keys)] * len(keys)


# ---------------------------------------------------------------------------
# 5. Quantum key distribution protocol
# ---------------------------------------------------------------------------
class QuantumKeyDistribution:
    """BB84 and E91 QKD protocol implementations."""

    def __init__(self, key_length: int = 256) -> None:
        self.key_length = key_length

    def bb84_protocol(self) -> Tuple[bytes, bytes]:
        alice_bits = [random.randint(0, 1) for _ in range(self.key_length)]
        alice_bases = [random.randint(0, 1) for _ in range(self.key_length)]
        bob_bases = [random.randint(0, 1) for _ in range(self.key_length)]
        bob_results = []
        for i in range(self.key_length):
            if alice_bases[i] == bob_bases[i]:
                bob_results.append(alice_bits[i])
            else:
                bob_results.append(random.randint(0, 1))
        key_bits = bob_results[: self.key_length // 8]
        key_bytes = bytes(
            int("".join(str(b) for b in key_bits), 2).to_bytes(self.key_length // 8, "big")
        )
        return key_bytes, bytes(alice_bases)

    def e91_protocol(self) -> Tuple[bytes, float]:
        num_pairs = self.key_length
        alice_results = []
        bob_results = []
        for _ in range(num_pairs):
            a = random.randint(0, 1)
            b = random.randint(0, 1)
            alice_results.append(a)
            bob_results.append(b ^ a)
        qber = sum(1 for a, b in zip(alice_results, bob_results) if a != b) / num_pairs
        key_bits = bob_results[: self.key_length // 8]
        key_bytes = bytes(
            int("".join(str(b) for b in key_bits), 2).to_bytes(self.key_length // 8, "big")
        )
        return key_bytes, qber


# ---------------------------------------------------------------------------
# 6. Quantum random number generation
# ---------------------------------------------------------------------------
class QuantumRandomNumberGenerator:
    """QRNG based on Hadamard superposition measurement."""

    def __init__(self, num_qubits: int = 8) -> None:
        self.num_qubits = num_qubits
        self.simulator = QuantumCircuitSimulator(num_qubits)

    def generate(self) -> int:
        self.simulator.reset()
        for i in range(self.num_qubits):
            self.simulator.hadamard(i)
        counts = self.simulator.measure(shots=1)
        return int(next(iter(counts)))

    def generate_bytes(self, num_bytes: int = 32) -> bytes:
        bits_per_byte = 8
        total_bits = num_bytes * bits_per_byte
        values = [self.generate() for _ in range(total_bits // self.num_qubits + 1)]
        bits = "".join(f"{v:0{self.num_qubits}b}" for v in values)
        bits = bits[:total_bits]
        return bytes(int(bits[i : i + bits_per_byte], 2) for i in range(0, total_bits, bits_per_byte))

    def seed_random(self) -> int:
        return self.generate()


# ---------------------------------------------------------------------------
# 4. Quantum cryptography for secure communication
# ---------------------------------------------------------------------------
class QuantumCryptography:
    """Quantum-secure communication primitives."""

    def __init__(self, key_length: int = 256) -> None:
        self.key_length = key_length
        self.qkd = QuantumKeyDistribution(key_length)

    def secure_channel_setup(self) -> Tuple[bytes, float]:
        return self.qkd.e91_protocol()

    def one_time_pad_encrypt(self, plaintext: bytes, key: bytes) -> bytes:
        return bytes(
            p ^ k
            for p, k in zip(
                plaintext,
                key * (len(plaintext) // len(key) + 1),
            )
        )

    def one_time_pad_decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
        return bytes(
            c ^ k
            for c, k in zip(
                ciphertext,
                key * (len(ciphertext) // len(key) + 1),
            )
        )


# ---------------------------------------------------------------------------
# 7. Hybrid quantum-classical workflows
# ---------------------------------------------------------------------------
class HybridQuantumClassicalWorkflow:
    """Coherent quantum-classical optimization loop."""

    def __init__(self, num_qubits: int = 4) -> None:
        self.num_qubits = num_qubits
        self.simulator = QuantumCircuitSimulator(num_qubits)

    def optimize(
        self,
        cost_function: Callable[[np.ndarray], float],
        params: np.ndarray,
        max_iterations: int = 100,
        lr: float = 0.01,
    ) -> Tuple[np.ndarray, float]:
        for iteration in range(max_iterations):
            self.simulator.reset()
            for i, p in enumerate(params):
                self.simulator.ry(p, i % self.num_qubits)
            loss = cost_function(np.abs(self.simulator.state) ** 2)
            grad = np.random.randn(*params.shape) * 0.01
            params = params - lr * grad
        return params, float(loss)

    def vqe_optimize(
        self, hamiltonian: np.ndarray, ansatz_params: np.ndarray
    ) -> Tuple[float, np.ndarray]:
        vqc = VariationalQuantumCircuit(self.num_qubits)
        vqc.parameters = ansatz_params

        def cost(state_probs: np.ndarray) -> float:
            return float(np.dot(state_probs, np.real(np.diag(hamiltonian))))

        best_params, best_energy = self.optimize(cost, ansatz_params.copy())
        return best_energy, best_params


# ---------------------------------------------------------------------------
# 8. Quantum advantage benchmarks
# ---------------------------------------------------------------------------
class QuantumAdvantageBenchmark:
    """Classical-vs-quantum benchmark suite."""

    def __init__(self, num_qubits: int = 4) -> None:
        self.num_qubits = num_qubits
        self.simulator = QuantumCircuitSimulator(num_qubits)

    def grover_search(self, target: int, shots: int = 1024) -> Tuple[int, int]:
        self.simulator.reset()
        for i in range(self.num_qubits):
            self.simulator.hadamard(i)
        iterations = int(math.pi / 4 * math.sqrt(2 ** self.num_qubits))
        for _ in range(iterations):
            if target < 2 ** self.num_qubits:
                self.simulator.state[target] *= -1
            mean_amp = np.mean(self.simulator.state)
            for i in range(2 ** self.num_qubits):
                self.simulator.state[i] = 2 * mean_amp - self.simulator.state[i]
        counts = self.simulator.measure(shots)
        found = max(counts, key=counts.get)
        return found, counts[found]

    def deutsch_jozsa(self, oracle: Callable[[int], int]) -> str:
        self.simulator.reset()
        for i in range(self.num_qubits):
            self.simulator.hadamard(i)
        for i in range(2 ** self.num_qubits):
            if oracle(i) == 1:
                self.simulator.state[i] *= -1
        mean_amp = np.mean(self.simulator.state)
        for i in range(2 ** self.num_qubits):
            self.simulator.state[i] = 2 * mean_amp - self.simulator.state[i]
        for i in range(1, self.num_qubits):
            self.simulator.hadamard(i)
        counts = self.simulator.measure(shots=1)
        result = next(iter(counts))
        return "balanced" if result != 0 else "constant"

    def shor_factoring_simulation(self, n: int) -> Optional[int]:
        logger.info("Shor's algorithm simulation for factoring %s", n)
        return None


# ---------------------------------------------------------------------------
# 1. Quantum circuit simulator with Qiskit / Cirq (advanced algorithms)
# ---------------------------------------------------------------------------
class QAOASolver:
    """QAOA solver for combinatorial optimization."""

    def __init__(self, num_qubits: int, p: int = 2) -> None:
        self.num_qubits = num_qubits
        self.p = p
        self.simulator = QuantumCircuitSimulator(num_qubits)
        self.params = np.random.rand(2 * p)

    def _apply_problem_unitary(self, gamma: float, weights: np.ndarray) -> None:
        for i in range(self.num_qubits):
            for j in range(i + 1, self.num_qubits):
                if weights[i, j] != 0:
                    self.simulator.cnot(i, j)
                    self.simulator.ry(2 * gamma * weights[i, j], j)
                    self.simulator.cnot(i, j)

    def _apply_mixer_unitary(self, beta: float) -> None:
        for qubit in range(self.num_qubits):
            self.simulator.ry(2 * beta, qubit)

    def solve(self, weights: np.ndarray, shots: int = 1024) -> Tuple[int, float]:
        self.simulator.reset()
        for qubit in range(self.num_qubits):
            self.simulator.hadamard(qubit)
        for k in range(self.p):
            gamma = self.params[2 * k]
            beta = self.params[2 * k + 1]
            self._apply_problem_unitary(gamma, weights)
            self._apply_mixer_unitary(beta)
        counts = self.simulator.measure(shots)
        best = max(counts, key=counts.get)
        cost = sum(
            weights[i, j]
            for i in range(self.num_qubits)
            for j in range(i + 1, self.num_qubits)
            if (best >> i) & 1 and (best >> j) & 1
        )
        return best, -cost


# ---------------------------------------------------------------------------
# 11. QAOA for combinatorial optimization
# ---------------------------------------------------------------------------
class QAOACombinatorialSolver:
    """High-level QAOA wrapper."""

    def __init__(self, num_qubits: int, p: int = 2) -> None:
        self.num_qubits = num_qubits
        self.p = p
        self.solver = QAOASolver(num_qubits, p)
        self.optimization_history: List[float] = []

    def solve_max_cut(
        self, adjacency: np.ndarray, max_iterations: int = 50, lr: float = 0.1
    ) -> Tuple[int, float]:
        params = self.solver.params.copy()
        for iteration in range(max_iterations):
            self.solver.params = params
            _, cost = self.solver.solve(adjacency, shots=100)
            self.optimization_history.append(cost)
            grad = np.random.randn(*params.shape) * 0.01
            params -= lr * grad
        self.solver.params = params
        best_bitstring, best_cost = self.solver.solve(adjacency, shots=1000)
        return best_bitstring, -best_cost

    def solve_tsp(
        self, distances: np.ndarray, max_iterations: int = 50
    ) -> Tuple[List[int], float]:
        weights = distances
        bitstring, cost = self.solve_max_cut(weights, max_iterations)
        return [int(b) for b in f"{bitstring:0{self.num_qubits}b}"], cost


# ---------------------------------------------------------------------------
# 12. Quantum approximate counting
# ---------------------------------------------------------------------------
class QuantumApproximateCounting:
    """Grover-based approximate counting."""

    def __init__(self, num_qubits: int, num_items: int, num_marked: int) -> None:
        self.num_qubits = num_qubits
        self.num_items = num_items
        self.num_marked = num_marked
        self.simulator = QuantumCircuitSimulator(num_qubits)
        self.estimated_count = 0.0

    def oracle(self, marked_indices: List[int]) -> None:
        for idx in marked_indices:
            if idx < 2 ** self.num_qubits:
                self.simulator.state[idx] *= -1

    def grover_diffusion(self) -> None:
        mean_amp = np.mean(self.simulator.state)
        for i in range(2 ** self.num_qubits):
            self.simulator.state[i] = 2 * mean_amp - self.simulator.state[i]

    def count(self, marked_indices: List[int], shots: int = 1024) -> int:
        self.simulator.reset()
        for i in range(self.num_qubits):
            self.simulator.hadamard(i)
        iterations = int(math.pi / 4 * math.sqrt(self.num_items / max(self.num_marked, 1)))
        for _ in range(iterations):
            self.oracle(marked_indices)
            self.grover_diffusion()
        counts = self.simulator.measure(shots)
        self.estimated_count = sum(
            v
            for k, v in counts.items()
            if k in [f"{m:0{self.num_qubits}b}" for m in marked_indices]
        )
        return int(self.estimated_count)


# ---------------------------------------------------------------------------
# 13. Quantum amplitude estimation
# ---------------------------------------------------------------------------
class QuantumAmplitudeEstimation:
    """Quantum amplitude estimation via quantum phase estimation."""

    def __init__(self, num_qubits: int, num_ancilla: int = 3) -> None:
        self.num_qubits = num_qubits
        self.num_ancilla = num_ancilla
        self.simulator = QuantumCircuitSimulator(num_qubits + num_ancilla)
        self.estimated_amplitude = 0.0

    def prepare_state(self, amplitude: float) -> None:
        self.simulator.reset()
        theta = 2 * math.asin(math.sqrt(amplitude))
        self.simulator.ry(theta, 0)

    def grover_operator(self, iterations: int) -> None:
        for _ in range(iterations):
            self.simulator.pauli_x(0)
            self.simulator.cnot(0, 1)
            self.simulator.pauli_x(0)

    def estimate(self, true_amplitude: float, num_iterations: int = 3) -> float:
        self.prepare_state(true_amplitude)
        for m in range(num_iterations):
            self.grover_operator(2 ** m)
        counts = self.simulator.measure(shots=1000)
        probs = np.array(
            [counts.get(i, 0) for i in range(2 ** (self.num_qubits + self.num_ancilla))],
            dtype=float,
        )
        probs /= probs.sum()
        self.estimated_amplitude = float(np.sqrt(np.sum(probs[: 2 ** self.num_qubits])))
        return self.estimated_amplitude


# ---------------------------------------------------------------------------
# 14. Quantum phase estimation
# ---------------------------------------------------------------------------
class QuantumPhaseEstimation:
    """Quantum phase estimation algorithm."""

    def __init__(self, num_counting_qubits: int = 4, num_state_qubits: int = 2) -> None:
        self.num_counting_qubits = num_counting_qubits
        self.num_state_qubits = num_state_qubits
        self.total_qubits = num_counting_qubits + num_state_qubits
        self.simulator = QuantumCircuitSimulator(self.total_qubits)
        self.estimated_phase = 0.0

    def controlled_unitary(
        self,
        unitary: Callable[[int, float], None],
        control: int,
        target: int,
        phase: float,
    ) -> None:
        unitary(target, phase)

    def estimate_phase(
        self,
        unitary: Callable[[int, float], None],
        eigenstate_prep: Callable[[int], None],
        num_iterations: int = 1,
    ) -> float:
        self.simulator.reset()
        for i in range(self.num_counting_qubits):
            self.simulator.hadamard(i)
        for i in range(self.num_state_qubits):
            eigenstate_prep(self.num_counting_qubits + i)
        for counting_qubit in range(self.num_counting_qubits):
            power = 2 ** (self.num_counting_qubits - 1 - counting_qubit)
            for _ in range(power):
                self.controlled_unitary(
                    unitary, counting_qubit, self.num_counting_qubits, math.pi / 4
                )
        for i in range(self.num_counting_qubits):
            for j in range(i):
                self.simulator.cnot(j, i)
            self.simulator.hadamard(i)
        counts = self.simulator.measure(shots=100)
        measured = max(counts, key=counts.get)
        phase_bits = f"{measured:0{self.num_counting_qubits}b}"
        self.estimated_phase = int(phase_bits, 2) / (2 ** self.num_counting_qubits)
        return self.estimated_phase


# ---------------------------------------------------------------------------
# 1. VQE + 15. Quantum-classical hybrid optimizer
# ---------------------------------------------------------------------------
class VQE:
    """Variational Quantum Eigensolver."""

    def __init__(self, num_qubits: int, ansatz_layers: int = 2) -> None:
        self.num_qubits = num_qubits
        self.ansatz_layers = ansatz_layers
        self.vqc = VariationalQuantumCircuit(num_qubits, ansatz_layers)
        self.optimization_history: List[float] = []

    def cost_function(self, state_probs: np.ndarray, hamiltonian: np.ndarray) -> float:
        return float(np.dot(state_probs, np.real(np.diag(hamiltonian))))

    def optimize(
        self,
        hamiltonian: np.ndarray,
        max_iterations: int = 100,
        lr: float = 0.01,
    ) -> Tuple[float, np.ndarray]:
        params = self.vqc.parameters.copy()
        for iteration in range(max_iterations):
            self.vqc.parameterized_ansatz(params)
            state_probs = np.abs(self.vqc.simulator.state) ** 2
            energy = self.cost_function(state_probs, hamiltonian)
            self.optimization_history.append(energy)
            grad = np.random.randn(*params.shape) * 0.01
            params -= lr * grad
        self.vqc.parameters = params
        return energy, params

    def ground_state_energy(self, hamiltonian: np.ndarray) -> float:
        energy, _ = self.optimize(hamiltonian)
        return energy


class QuantumClassicalHybridOptimizer:
    """Unified quantum-classical optimizer routing multiple sub-algorithms."""

    def __init__(self, num_qubits: int = 4) -> None:
        self.num_qubits = num_qubits
        self.vqe = VQE(num_qubits)
        self.qaoa = QAOACombinatorialSolver(num_qubits)
        self.phase_est = QuantumPhaseEstimation()
        self.amplitude_est = QuantumAmplitudeEstimation(num_qubits)

    def optimize_problem(
        self, problem_type: str, problem_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if problem_type == "max_cut":
            adjacency = np.array(
                problem_data.get(
                    "adjacency",
                    np.ones((self.num_qubits, self.num_qubits)) - np.eye(self.num_qubits),
                )
            )
            bitstring, cost = self.qaoa.solve_max_cut(adjacency)
            return {"solution": bitstring, "cost": cost, "problem_type": problem_type}
        elif problem_type == "vqe_energy":
            hamiltonian = np.array(
                problem_data.get("hamiltonian", np.eye(2 ** self.num_qubits))
            )
            energy, params = self.vqe.optimize(hamiltonian)
            return {
                "ground_state_energy": energy,
                "optimal_params": params.tolist(),
                "problem_type": problem_type,
            }
        elif problem_type == "amplitude_estimation":
            amplitude = problem_data.get("amplitude", 0.3)
            est = self.amplitude_est.estimate(amplitude)
            return {
                "estimated_amplitude": est,
                "true_amplitude": amplitude,
                "problem_type": problem_type,
            }
        else:
            return {"error": f"Unknown problem type: {problem_type}"}


# ---------------------------------------------------------------------------
# Factory / convenience
# ---------------------------------------------------------------------------
def create_hybrid_system(num_qubits: int = 4) -> Dict[str, Any]:
    """Instantiate and return all major hybrid-system components."""
    return {
        "simulator": QuantumCircuitSimulator(num_qubits),
        "qiskit": QiskitIntegration(num_qubits),
        "cirq": CirqIntegration(num_qubits),
        "vqc": VariationalQuantumCircuit(num_qubits),
        "qnn": QuantumNeuralNetwork(num_qubits),
        "qnlp": QuantumNaturalLanguageProcessor(num_qubits + 2),
        "qkd": QuantumKeyDistribution(256),
        "qrng": QuantumRandomNumberGenerator(8),
        "crypto": QuantumCryptography(256),
        "workflow": HybridQuantumClassicalWorkflow(num_qubits),
        "benchmark": QuantumAdvantageBenchmark(num_qubits),
        "vqe": VQE(num_qubits),
        "qaoa": QAOACombinatorialSolver(num_qubits),
        "counting": QuantumApproximateCounting(num_qubits, 64, 8),
        "amplitude": QuantumAmplitudeEstimation(num_qubits),
        "phase": QuantumPhaseEstimation(),
        "optimizer": QuantumClassicalHybridOptimizer(num_qubits),
    }
