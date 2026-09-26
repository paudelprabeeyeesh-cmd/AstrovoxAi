import numpy as np
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

class GateType(Enum):
    H = "h"
    X = "x"
    Y = "y"
    Z = "z"
    RX = "rx"
    RY = "ry"
    RZ = "rz"
    CNOT = "cnot"
    SWAP = "swap"
    TOFFOLI = "toffoli"
    PHASE = "phase"
    S = "s"
    T = "t"
    U3 = "u3"

@dataclass
class Gate:
    gate_type: GateType
    qubits: List[int]
    params: List[float] = field(default_factory=list)

@dataclass
class MeasurementResult:
    counts: Dict[str, int]
    shots: int
    probabilities: Dict[str, float]

class QuantumCircuitSimulator:
    def __init__(self, num_qubits: int, seed: Optional[int] = None):
        self.num_qubits = num_qubits
        self.gates: List[Gate] = []
        self.measurements: List[int] = []
        self.state: np.ndarray = np.zeros(2 ** num_qubits, dtype=np.complex128)
        self.state[0] = 1.0 + 0.0j
        if seed is not None:
            np.random.seed(seed)

    def add_gate(self, gate_type: Union[GateType, str], qubits: List[int], params: Optional[List[float]] = None) -> "QuantumCircuitSimulator":
        if isinstance(gate_type, str):
            gate_type = GateType(gate_type.lower())
        self.gates.append(Gate(gate_type=gate_type, qubits=qubits, params=params or []))
        return self

    def h(self, qubit: int) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.H, [qubit])

    def x(self, qubit: int) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.X, [qubit])

    def y(self, qubit: int) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.Y, [qubit])

    def z(self, qubit: int) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.Z, [qubit])

    def rx(self, qubit: int, theta: float) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.RX, [qubit], [theta])

    def ry(self, qubit: int, theta: float) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.RY, [qubit], [theta])

    def rz(self, qubit: int, theta: float) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.RZ, [qubit], [theta])

    def cnot(self, control: int, target: int) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.CNOT, [control, target])

    def swap(self, qubit1: int, qubit2: int) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.SWAP, [qubit1, qubit2])

    def toffoli(self, c1: int, c2: int, target: int) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.TOFFOLI, [c1, c2, target])

    def phase(self, qubit: int, phi: float) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.PHASE, [qubit], [phi])

    def u3(self, qubit: int, theta: float, phi: float, lam: float) -> "QuantumCircuitSimulator":
        return self.add_gate(GateType.U3, [qubit], [theta, phi, lam])

    def _apply_single_qubit(self, matrix: np.ndarray, qubit: int) -> None:
        dim = 2 ** self.num_qubits
        result = np.zeros(dim, dtype=np.complex128)
        for i in range(dim):
            bit = (i >> (self.num_qubits - qubit - 1)) & 1
            if bit == 0:
                j = i
                k = i | (1 << (self.num_qubits - qubit - 1))
            else:
                j = i | (1 << (self.num_qubits - qubit - 1))
                k = i
            result[i] = matrix[bit, bit] * self.state[i] + matrix[bit, 1 - bit] * self.state[j if bit == 0 else k]
        self.state = result

    def _apply_two_qubit(self, matrix: np.ndarray, control: int, target: int) -> None:
        dim = 2 ** self.num_qubits
        ctrl_bit = 1 << (self.num_qubits - control - 1)
        targ_bit = 1 << (self.num_qubits - target - 1)
        new_state = self.state.copy()
        for i in range(dim):
            if (i & ctrl_bit) != 0:
                j = i ^ targ_bit
                row = 1 if (i & targ_bit) != 0 else 0
                col = 1 if (j & targ_bit) != 0 else 0
                new_state[i] = matrix[row, 0] * self.state[j ^ targ_bit] + matrix[row, 1] * self.state[j]
        self.state = new_state

    def _apply_gate_matrix(self, gate: Gate) -> None:
        gt = gate.gate_type
        q = gate.qubits
        if gt == GateType.H:
            mat = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
            self._apply_single_qubit(mat, q[0])
        elif gt == GateType.X:
            mat = np.array([[0, 1], [1, 0]], dtype=np.complex128)
            self._apply_single_qubit(mat, q[0])
        elif gt == GateType.Y:
            mat = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
            self._apply_single_qubit(mat, q[0])
        elif gt == GateType.Z:
            mat = np.array([[1, 0], [0, -1]], dtype=np.complex128)
            self._apply_single_qubit(mat, q[0])
        elif gt == GateType.RX:
            theta = gate.params[0]
            mat = np.array([[np.cos(theta / 2), -1j * np.sin(theta / 2)], [-1j * np.sin(theta / 2), np.cos(theta / 2)]], dtype=np.complex128)
            self._apply_single_qubit(mat, q[0])
        elif gt == GateType.RY:
            theta = gate.params[0]
            mat = np.array([[np.cos(theta / 2), -np.sin(theta / 2)], [np.sin(theta / 2), np.cos(theta / 2)]], dtype=np.complex128)
            self._apply_single_qubit(mat, q[0])
        elif gt == GateType.RZ:
            theta = gate.params[0]
            mat = np.array([[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]], dtype=np.complex128)
            self._apply_single_qubit(mat, q[0])
        elif gt == GateType.S:
            mat = np.array([[1, 0], [0, 1j]], dtype=np.complex128)
            self._apply_single_qubit(mat, q[0])
        elif gt == GateType.T:
            mat = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=np.complex128)
            self._apply_single_qubit(mat, q[0])
        elif gt == GateType.PHASE:
            phi = gate.params[0]
            mat = np.array([[1, 0], [0, np.exp(1j * phi)]], dtype=np.complex128)
            self._apply_single_qubit(mat, q[0])
        elif gt == GateType.CNOT:
            mat = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=np.complex128)
            self._apply_two_qubit(mat.reshape(2, 2, 2, 2), q[0], q[1])
        elif gt == GateType.SWAP:
            mat = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=np.complex128)
            self._apply_two_qubit(mat.reshape(2, 2, 2, 2), q[0], q[1])
        elif gt == GateType.TOFFOLI:
            mat = np.eye(8, dtype=np.complex128)
            mat[6, 6] = 0
            mat[6, 7] = 1
            mat[7, 6] = 1
            mat[7, 7] = 0
            self._apply_three_qubit(mat, q[0], q[1], q[2])
        elif gt == GateType.U3:
            theta, phi, lam = gate.params
            mat = np.array([
                [np.cos(theta / 2), -np.exp(1j * lam) * np.sin(theta / 2)],
                [np.exp(1j * phi) * np.sin(theta / 2), np.exp(1j * (phi + lam)) * np.cos(theta / 2)]
            ], dtype=np.complex128)
            self._apply_single_qubit(mat, q[0])

    def _apply_three_qubit(self, matrix: np.ndarray, q1: int, q2: int, q3: int) -> None:
        dim = 2 ** self.num_qubits
        new_state = self.state.copy()
        b1 = 1 << (self.num_qubits - q1 - 1)
        b2 = 1 << (self.num_qubits - q2 - 1)
        b3 = 1 << (self.num_qubits - q3 - 1)
        for i in range(dim):
            if (i & b1) and (i & b2):
                j = i ^ b3
                new_state[i] = matrix[i, i] * self.state[i] + matrix[i, j] * self.state[j]
        self.state = new_state

    def run(self, shots: int = 1024) -> MeasurementResult:
        self._execute()
        probs = np.abs(self.state) ** 2
        probs = probs / probs.sum()
        outcomes = np.random.choice(2 ** self.num_qubits, size=shots, p=probs)
        counts: Dict[str, int] = {}
        for outcome in outcomes:
            key = format(outcome, f"0{self.num_qubits}b")
            counts[key] = counts.get(key, 0) + 1
        prob_dict = {format(i, f"0{self.num_qubits}b"): float(p) for i, p in enumerate(probs)}
        return MeasurementResult(counts=counts, shots=shots, probabilities=prob_dict)

    def _execute(self) -> None:
        for gate in self.gates:
            self._apply_gate_matrix(gate)

    def get_statevector(self) -> np.ndarray:
        self._execute()
        return self.state.copy()

    def get_probabilities(self) -> Dict[str, float]:
        probs = np.abs(self.get_statevector()) ** 2
        probs = probs / probs.sum()
        return {format(i, f"0{self.num_qubits}b"): float(p) for i, p in enumerate(probs) if p > 1e-10}

    def expectation(self, observable: np.ndarray) -> float:
        state = self.get_statevector()
        return float(np.real(np.conj(state) @ observable @ state))

    def reset(self) -> None:
        self.state = np.zeros(2 ** self.num_qubits, dtype=np.complex128)
        self.state[0] = 1.0 + 0.0j
        self.gates = []

    def to_dict(self) -> Dict:
        return {
            "num_qubits": self.num_qubits,
            "gates": [
                {"type": g.gate_type.value, "qubits": g.qubits, "params": g.params}
                for g in self.gates
            ],
            "statevector_norm": float(np.linalg.norm(self.get_statevector())),
        }

    def __repr__(self) -> str:
        return f"QuantumCircuitSimulator(qubits={self.num_qubits}, gates={len(self.gates)})"


def simulate_circuit(num_qubits: int, gates: List[Dict], shots: int = 1024) -> Dict:
    sim = QuantumCircuitSimulator(num_qubits)
    for g in gates:
        sim.add_gate(g["type"], g["qubits"], g.get("params", []))
    result = sim.run(shots=shots)
    return {
        "counts": result.counts,
        "probabilities": result.probabilities,
        "shots": result.shots,
    }
