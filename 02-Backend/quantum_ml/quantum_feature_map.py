import numpy as np
from typing import Optional
from .quantum_circuits import QuantumCircuit


class FeatureMap:
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits

    def encode(self, x: np.ndarray) -> QuantumCircuit:
        raise NotImplementedError


class ZZFeatureMap(FeatureMap):
    def encode(self, x: np.ndarray) -> QuantumCircuit:
        circuit = QuantumCircuit(self.num_qubits)
        for i in range(self.num_qubits):
            circuit.h(i)
            circuit.ry(i, x[i % len(x)])
        for i in range(self.num_qubits - 1):
            circuit.rz(i + 1, 2 * x[i % len(x)] * x[(i + 1) % len(x)])
            circuit.cnot(i, i + 1)
        for i in range(self.num_qubits):
            circuit.h(i)
            circuit.ry(i, x[i % len(x)])
        return circuit


class PauliFeatureMap(FeatureMap):
    def encode(self, x: np.ndarray) -> QuantumCircuit:
        circuit = QuantumCircuit(self.num_qubits)
        for i in range(self.num_qubits):
            circuit.h(i)
            circuit.rz(i, x[i % len(x)])
        for i in range(self.num_qubits - 1):
            circuit.cnot(i, i + 1)
            circuit.rz(i + 1, np.pi / 2 * (x[i % len(x)] + x[(i + 1) % len(x)]))
            circuit.cnot(i, i + 1)
        return circuit
