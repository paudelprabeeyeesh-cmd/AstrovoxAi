import numpy as np
from typing import Union, Dict
from .quantum_circuits import QuantumCircuit


class QuantumMeasurement:
    @staticmethod
    def measure_z(state: np.ndarray) -> float:
        num_qubits = int(np.log2(len(state)))
        expectation = 0.0
        for i in range(len(state)):
            bits = [(i >> (num_qubits - 1 - j)) & 1 for j in range(num_qubits)]
            parity = (-1)**sum(bits)
            prob = np.abs(state[i])**2
            expectation += parity * prob
        return float(expectation)

    @staticmethod
    def measure_x(state: np.ndarray) -> float:
        num_qubits = int(np.log2(len(state)))
        h_gate = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
        dim = 2**num_qubits
        full_h = np.eye(dim, dtype=np.complex128)
        for i in range(num_qubits):
            gate = np.eye(1, dtype=np.complex128)
            for j in range(num_qubits):
                if j == i:
                    gate = np.kron(gate, h_gate)
                else:
                    gate = np.kron(gate, np.eye(2, dtype=np.complex128))
            full_h = gate @ full_h
        state_h = full_h @ state
        return QuantumMeasurement.measure_z(state_h)

    @staticmethod
    def measure_y(state: np.ndarray) -> float:
        num_qubits = int(np.log2(len(state)))
        sdag_h = np.array([[1, -1j], [1, 1j]], dtype=np.complex128) / np.sqrt(2)
        dim = 2**num_qubits
        full_sdagh = np.eye(dim, dtype=np.complex128)
        for i in range(num_qubits):
            gate = np.eye(1, dtype=np.complex128)
            for j in range(num_qubits):
                if j == i:
                    gate = np.kron(gate, sdag_h)
                else:
                    gate = np.kron(gate, np.eye(2, dtype=np.complex128))
            full_sdagh = gate @ full_sdagh
        state_sdagh = full_sdagh @ state
        return QuantumMeasurement.measure_z(state_sdagh)

    @staticmethod
    def expectation_pauli(state: np.ndarray, pauli: str, qubit: int) -> float:
        if pauli == "Z":
            return QuantumMeasurement.measure_single_z(state, qubit)
        elif pauli == "X":
            return QuantumMeasurement.measure_single_x(state, qubit)
        elif pauli == "Y":
            return QuantumMeasurement.measure_single_y(state, qubit)
        else:
            raise ValueError(f"Unknown Pauli operator: {pauli}")

    @staticmethod
    def measure_single_z(state: np.ndarray, qubit: int) -> float:
        num_qubits = int(np.log2(len(state)))
        expectation = 0.0
        for i in range(len(state)):
            bit = (i >> (num_qubits - 1 - qubit)) & 1
            prob = np.abs(state[i])**2
            expectation += (1 if bit == 0 else -1) * prob
        return float(expectation)

    @staticmethod
    def measure_single_x(state: np.ndarray, qubit: int) -> float:
        num_qubits = int(np.log2(len(state)))
        h_gate = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
        dim = 2**num_qubits
        full_h = np.eye(dim, dtype=np.complex128)
        for i in range(num_qubits):
            gate = np.eye(1, dtype=np.complex128)
            for j in range(num_qubits):
                if j == i:
                    gate = np.kron(gate, h_gate)
                else:
                    gate = np.kron(gate, np.eye(2, dtype=np.complex128))
            full_h = gate @ full_h
        state_h = full_h @ state
        return QuantumMeasurement.measure_single_z(state_h, qubit)

    @staticmethod
    def measure_single_y(state: np.ndarray, qubit: int) -> float:
        num_qubits = int(np.log2(len(state)))
        s_gate = np.array([[1, -1j], [1j, -1j]], dtype=np.complex128) / np.sqrt(2)
        dim = 2**num_qubits
        full_s = np.eye(dim, dtype=np.complex128)
        for i in range(num_qubits):
            gate = np.eye(1, dtype=np.complex128)
            for j in range(num_qubits):
                if j == i:
                    gate = np.kron(gate, s_gate)
                else:
                    gate = np.kron(gate, np.eye(2, dtype=np.complex128))
            full_s = gate @ full_s
        state_s = full_s @ state
        return QuantumMeasurement.measure_single_z(state_s, qubit)

    @staticmethod
    def measure_circuit(circuit: QuantumCircuit, shots: int = 1024) -> Dict[str, int]:
        probs = np.abs(circuit.state)**2
        outcomes = np.random.choice(len(probs), size=shots, p=probs)
        counts = {}
        for outcome in outcomes:
            bitstring = format(outcome, f"0{circuit.num_qubits}b")
            counts[bitstring] = counts.get(bitstring, 0) + 1
        return counts

    @staticmethod
    def expectation_value(state: np.ndarray, operator: np.ndarray) -> float:
        return float(np.real(np.conj(state) @ operator @ state))
