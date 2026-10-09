import numpy as np
from typing import List, Tuple
from .quantum_circuits import QuantumCircuit


class ClassicalToQuantum:
    @staticmethod
    def amplitude_encoding(data: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(data)
        if norm < 1e-10:
            return np.zeros(len(data), dtype=np.complex128)
        return data / norm

    @staticmethod
    def angle_encoding(data: np.ndarray, rotation: str = "y") -> List[Tuple[str, int, float]]:
        gates = []
        for i, val in enumerate(data):
            gates.append((rotation, i, float(val * np.pi)))
        return gates

    @staticmethod
    def basis_encoding(data: np.ndarray) -> str:
        bits = []
        for val in data:
            bits.append("1" if val > 0 else "0")
        return "".join(bits)

    @staticmethod
    def phase_encoding(data: np.ndarray) -> np.ndarray:
        n = len(data)
        padded = np.zeros(2**int(np.ceil(np.log2(n))) - n)
        extended = np.concatenate([data, padded])
        fft = np.fft.fft(extended)
        return np.angle(fft)

    @staticmethod
    def qsample_encoding(data: np.ndarray, num_qubits: int) -> QuantumCircuit:
        circuit = QuantumCircuit(num_qubits)
        probabilities = np.abs(data) / (np.linalg.norm(data) + 1e-10)
        for i in range(num_qubits):
            ry_angle = 2 * np.arcsin(np.sqrt(np.clip(np.sum(probabilities[2**i:2**(i+1)]), 0, 1)))
            circuit.ry(i, ry_angle)
        for i in range(num_qubits - 1):
            circuit.cnot(i, i + 1)
        return circuit

    @staticmethod
    def squeeze_encoding(data: np.ndarray, num_qubits: int) -> QuantumCircuit:
        circuit = QuantumCircuit(num_qubits)
        mean = np.mean(data)
        std = np.std(data) + 1e-10
        normalized = (data - mean) / std
        for i in range(min(len(normalized), num_qubits)):
            circuit.ry(i, np.clip(normalized[i], -np.pi, np.pi))
        return circuit

    @staticmethod
    def tensor_encoding(data: np.ndarray, num_qubits: int) -> QuantumCircuit:
        circuit = QuantumCircuit(num_qubits)
        for i in range(num_qubits):
            idx = i % len(data)
            circuit.h(i)
            circuit.rz(i, float(data[idx]))
        return circuit
