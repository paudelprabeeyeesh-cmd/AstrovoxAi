import numpy as np
from typing import Union, List
from .quantum_circuits import QuantumCircuit


class QuantumEmbedding:
    @staticmethod
    def amplitude_encode(classical_data: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(classical_data)
        if norm == 0:
            return np.zeros(len(classical_data), dtype=np.complex128)
        return classical_data / norm

    @staticmethod
    def angle_encode(classical_data: np.ndarray, rotation: str = "y") -> np.ndarray:
        num_qubits = int(np.ceil(np.log2(len(classical_data))))
        total_states = 2**num_qubits
        padded = np.zeros(total_states)
        padded[:len(classical_data)] = classical_data
        angles = np.arccos(np.clip(padded / (np.linalg.norm(padded) + 1e-10), -1, 1))
        return angles

    @staticmethod
    def basis_encode(classical_data: np.ndarray) -> List[int]:
        return [int(x > 0) for x in classical_data]

    @staticmethod
    def phase_encode(classical_data: np.ndarray) -> np.ndarray:
        fft = np.fft.fft(classical_data)
        phases = np.angle(fft)
        return phases

    @staticmethod
    def iqp_encode(features: np.ndarray, depth: int = 2) -> QuantumCircuit:
        num_qubits = len(features)
        circuit = QuantumCircuit(num_qubits)
        for i in range(num_qubits):
            circuit.h(i)
            circuit.ry(i, features[i])
        for d in range(depth):
            for i in range(num_qubits):
                for j in range(i + 1, num_qubits):
                    circuit.cnot(i, j)
                    circuit.rz(j, features[i] * features[j] * np.pi)
                    circuit.cnot(i, j)
            for i in range(num_qubits):
                circuit.ry(i, features[i] * np.pi / (d + 1))
        return circuit

    @staticmethod
    def amplitude_embedding(circuit: QuantumCircuit, data: np.ndarray) -> QuantumCircuit:
        normalized = data / (np.linalg.norm(data) + 1e-10)
        state = circuit.state.copy()
        dim = len(state)
        n = len(normalized)
        for i in range(min(n, dim)):
            state[i] = normalized[i] * np.exp(1j * np.angle(state[i]))
        circuit.state = state
        return circuit
