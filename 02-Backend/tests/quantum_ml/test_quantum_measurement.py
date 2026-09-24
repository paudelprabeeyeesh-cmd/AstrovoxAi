import numpy as np
from quantum_ml.quantum_measurement import QuantumMeasurement
from quantum_ml.quantum_circuits import QuantumCircuit


class TestQuantumMeasurement:
    def test_measure_z_plus(self):
        state = np.array([1, 0], dtype=np.complex128)
        assert abs(QuantumMeasurement.measure_z(state) - 1.0) < 1e-10

    def test_measure_z_minus(self):
        state = np.array([0, 1], dtype=np.complex128)
        assert abs(QuantumMeasurement.measure_z(state) + 1.0) < 1e-10

    def test_measure_x_plus(self):
        state = np.array([1, 1], dtype=np.complex128) / np.sqrt(2)
        assert abs(QuantumMeasurement.measure_x(state) - 1.0) < 1e-10

    def test_measure_x_minus(self):
        state = np.array([1, -1], dtype=np.complex128) / np.sqrt(2)
        assert abs(QuantumMeasurement.measure_x(state) + 1.0) < 1e-10

    def test_measure_y_plus(self):
        state = np.array([1, 1j], dtype=np.complex128) / np.sqrt(2)
        assert abs(QuantumMeasurement.measure_y(state) - 1.0) < 1e-10

    def test_expectation_pauli_z(self):
        state = np.array([1, 0], dtype=np.complex128)
        assert abs(QuantumMeasurement.expectation_pauli(state, "Z", 0) - 1.0) < 1e-10

    def test_expectation_pauli_x(self):
        state = np.array([1, 1], dtype=np.complex128) / np.sqrt(2)
        assert abs(QuantumMeasurement.expectation_pauli(state, "X", 0) - 1.0) < 1e-10

    def test_measure_circuit_counts(self):
        circuit = QuantumCircuit(2)
        circuit.h(0).h(1)
        counts = QuantumMeasurement.measure_circuit(circuit, shots=100)
        assert sum(counts.values()) == 100

    def test_expectation_value_identity(self):
        state = np.array([1, 0], dtype=np.complex128)
        op = np.eye(2)
        assert abs(QuantumMeasurement.expectation_value(state, op) - 1.0) < 1e-10

    def test_expectation_value_z(self):
        state = np.array([0, 1], dtype=np.complex128)
        op = np.array([[1, 0], [0, -1]], dtype=np.complex128)
        assert abs(QuantumMeasurement.expectation_value(state, op) + 1.0) < 1e-10
