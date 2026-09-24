import numpy as np
from typing import List, Tuple, Union, Optional


class QuantumCircuit:
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.state = np.zeros(2**num_qubits, dtype=np.complex128)
        self.state[0] = 1.0 + 0.0j
        self.gates: List[Tuple[str, List[int], Optional[np.ndarray], Optional[float]]] = []

    def h(self, target: int) -> "QuantumCircuit":
        h_gate = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
        self.gates.append(("h", [target], h_gate, None))
        return self

    def x(self, target: int) -> "QuantumCircuit":
        x_gate = np.array([[0, 1], [1, 0]], dtype=np.complex128)
        self.gates.append(("x", [target], x_gate, None))
        return self

    def y(self, target: int) -> "QuantumCircuit":
        y_gate = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
        self.gates.append(("y", [target], y_gate, None))
        return self

    def z(self, target: int) -> "QuantumCircuit":
        z_gate = np.array([[1, 0], [0, -1]], dtype=np.complex128)
        self.gates.append(("z", [target], z_gate, None))
        return self

    def rx(self, target: int, theta: float) -> "QuantumCircuit":
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        rx_gate = np.array([[c, -1j * s], [-1j * s, c]], dtype=np.complex128)
        self.gates.append(("rx", [target], rx_gate, theta))
        return self

    def ry(self, target: int, theta: float) -> "QuantumCircuit":
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        ry_gate = np.array([[c, -s], [s, c]], dtype=np.complex128)
        self.gates.append(("ry", [target], ry_gate, theta))
        return self

    def rz(self, target: int, theta: float) -> "QuantumCircuit":
        rz_gate = np.array([[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]], dtype=np.complex128)
        self.gates.append(("rz", [target], rz_gate, theta))
        return self

    def cx(self, control: int, target: int) -> "QuantumCircuit":
        cx_gate = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=np.complex128)
        self.gates.append(("cx", [control, target], cx_gate, None))
        return self

    def cnot(self, control: int, target: int) -> "QuantumCircuit":
        return self.cx(control, target)

    def measure(self, shots: int = 1024) -> dict:
        self.run()
        probs = np.abs(self.state)**2
        outcomes = np.random.choice(len(probs), size=shots, p=probs)
        counts = {}
        for outcome in outcomes:
            bitstring = format(outcome, f"0{self.num_qubits}b")
            counts[bitstring] = counts.get(bitstring, 0) + 1
        return counts

    def _apply_gate(self, gate_matrix: np.ndarray, targets: List[int]) -> None:
        dim = 2**self.num_qubits
        full_matrix = np.eye(dim, dtype=np.complex128)
        target_dim = 2**len(targets)
        for i in range(dim):
            bits = [(i >> (self.num_qubits - 1 - j)) & 1 for j in range(self.num_qubits)]
            target_bits = [bits[t] for t in targets]
            target_idx = sum(b << (len(targets) - 1 - j) for j, b in enumerate(target_bits))
            for j in range(target_dim):
                new_target_bits = [(j >> (len(targets) - 1 - k)) & 1 for k in range(len(targets))]
                new_bits = bits[:]
                for idx, t in enumerate(targets):
                    new_bits[t] = new_target_bits[idx]
                new_idx = sum(b << (self.num_qubits - 1 - k) for k, b in enumerate(new_bits))
                full_matrix[new_idx, i] = gate_matrix[j, target_idx]
        self.state = full_matrix @ self.state

    def run(self) -> np.ndarray:
        for gate_name, targets, gate_matrix, _ in self.gates:
            if gate_matrix is not None:
                self._apply_gate(gate_matrix, targets)
        return self.state

    def statevector(self) -> np.ndarray:
        self.run()
        return self.state.copy()

    @staticmethod
    def decompose_unitary(U: np.ndarray) -> List[np.ndarray]:
        qr = np.linalg.qr(U)
        gates = []
        for i in range(min(U.shape) - 1):
            if not np.allclose(qr[0][i, i], 0):
                gates.append(qr[0][:, i].reshape(-1, 1))
        return gates

    def reset(self) -> None:
        self.state = np.zeros(2**self.num_qubits, dtype=np.complex128)
        self.state[0] = 1.0 + 0.0j
        self.gates = []


class GateDecomposer:
    @staticmethod
    def decompose_rotation(theta: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        c, s = np.cos(theta / 2), np.sin(theta / 2)
        return (
            np.array([[c, -1j * s], [-1j * s, c]], dtype=np.complex128),
            np.array([[c, -s], [s, c]], dtype=np.complex128),
            np.array([[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]], dtype=np.complex128),
        )

    @staticmethod
    def cz() -> np.ndarray:
        return np.diag([1, 1, 1, -1]).astype(np.complex128)

    @staticmethod
    def swap() -> np.ndarray:
        return np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=np.complex128)
