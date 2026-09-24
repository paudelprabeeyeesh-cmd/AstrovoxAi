import numpy as np
import pytest
from quantum_ml.quantum_data_encoding import ClassicalToQuantum
from quantum_ml.quantum_circuits import QuantumCircuit


class TestClassicalToQuantum:
    def test_amplitude_encoding_normalization(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        encoded = ClassicalToQuantum.amplitude_encoding(data)
        assert abs(np.linalg.norm(encoded) - 1.0) < 1e-10

    def test_amplitude_encoding_zero(self):
        data = np.array([0.0, 0.0, 0.0])
        encoded = ClassicalToQuantum.amplitude_encoding(data)
        np.testing.assert_allclose(encoded, np.zeros(3), atol=1e-10)

    def test_angle_encoding_length(self):
        data = np.array([0.1, 0.5, 0.9])
        gates = ClassicalToQuantum.angle_encoding(data)
        assert len(gates) == 3

    def test_angle_encoding_gate_types(self):
        data = np.array([0.1, 0.5])
        gates = ClassicalToQuantum.angle_encoding(data)
        assert all(g[0] == "y" for g in gates)

    def test_basis_encoding(self):
        data = np.array([1.0, -1.0, 0.5])
        bits = ClassicalToQuantum.basis_encoding(data)
        assert bits == "101"

    def test_phase_encoding_shape(self):
        data = np.array([1.0, 2.0, 3.0])
        phases = ClassicalToQuantum.phase_encoding(data)
        assert len(phases) == 4

    def test_qsample_encoding(self):
        data = np.array([1.0, 0.0, 0.0, 0.0])
        circuit = ClassicalToQuantum.qsample_encoding(data, num_qubits=2)
        assert isinstance(circuit, QuantumCircuit)
        assert circuit.num_qubits == 2

    def test_squeeze_encoding(self):
        data = np.array([1.0, 2.0, 3.0])
        circuit = ClassicalToQuantum.squeeze_encoding(data, num_qubits=3)
        assert isinstance(circuit, QuantumCircuit)

    def test_tensor_encoding(self):
        data = np.array([1.0, 0.5, 0.25])
        circuit = ClassicalToQuantum.tensor_encoding(data, num_qubits=3)
        assert isinstance(circuit, QuantumCircuit)
        assert circuit.num_qubits == 3
