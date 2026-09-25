from typing import Optional, Dict, Any, List, Callable
import numpy as np
from abc import ABC, abstractmethod


class QuantumCircuit(ABC):
    @abstractmethod
    def h(self, qubit: int) -> None:
        pass

    @abstractmethod
    def cx(self, control: int, target: int) -> None:
        pass

    @abstractmethod
    def measure(self, qubit: int) -> int:
        pass

    @abstractmethod
    def simulate(self, shots: int = 1024) -> Dict[int, int]:
        pass


class QuantumAlgorithmSimulator(QuantumCircuit):
    def __init__(self, num_qubits: int = 4):
        self.num_qubits = num_qubits
        self.state = np.zeros(2 ** num_qubits, dtype=complex)
        self.state[0] = 1.0
        self.operations: List[str] = []

    def h(self, qubit: int) -> None:
        self.operations.append(f'H({qubit})')
        h_matrix = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
        self._apply_single_qubit(qubit, h_matrix)

    def cx(self, control: int, target: int) -> None:
        self.operations.append(f'CNOT({control},{target})')
        cnot = np.eye(2 ** self.num_qubits)
        for i in range(2 ** self.num_qubits):
            if (i >> control) & 1:
                j = i ^ (1 << target)
                cnot[i, i], cnot[i, j] = 0, 1
        self.state = cnot @ self.state

    def measure(self, qubit: int) -> int:
        probs = np.abs(self.state) ** 2
        return np.random.choice(2 ** self.num_qubits, p=probs)

    def simulate(self, shots: int = 1024) -> Dict[int, int]:
        probs = np.abs(self.state) ** 2
        outcomes = np.random.choice(2 ** self.num_qubits, size=shots, p=probs)
        counts = {}
        for outcome in outcomes:
            counts[outcome] = counts.get(outcome, 0) + 1
        return counts

    def _apply_single_qubit(self, qubit: int, matrix: np.ndarray) -> None:
        for i in range(2 ** self.num_qubits):
            if (i >> qubit) & 1 == 0 and (i >> qubit) & 1 == 0:
                j = i ^ (1 << qubit)
                a, b = self.state[i], self.state[j]
                self.state[i] = matrix[0, 0] * a + matrix[0, 1] * b
                self.state[j] = matrix[1, 0] * a + matrix[1, 1] * b

    def reset(self) -> None:
        self.state = np.zeros(2 ** self.num_qubits, dtype=complex)
        self.state[0] = 1.0
        self.operations = []
