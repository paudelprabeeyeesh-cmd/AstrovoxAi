import numpy as np
import pytest
from quantum_ml.quantum_circuits import QuantumCircuit, GateDecomposer


class TestQuantumCircuit:
    def test_single_qubit_hadamard(self):
        circuit = QuantumCircuit(1)
        circuit.h(0)
        state = circuit.statevector()
        expected = np.array([1, 1]) / np.sqrt(2)
        np.testing.assert_allclose(np.abs(state), np.abs(expected), atol=1e-10)

    def test_single_qubit_x(self):
        circuit = QuantumCircuit(1)
        circuit.x(0)
        state = circuit.statevector()
        np.testing.assert_allclose(state, np.array([0, 1], dtype=np.complex128), atol=1e-10)

    def test_single_qubit_z(self):
        circuit = QuantumCircuit(1)
        circuit.z(0)
        state = circuit.statevector()
        np.testing.assert_allclose(state, np.array([1, 0], dtype=np.complex128), atol=1e-10)

    def test_cnot_gate(self):
        circuit = QuantumCircuit(2)
        circuit.x(0).cx(0, 1)
        state = circuit.statevector()
        np.testing.assert_allclose(state, np.array([0, 0, 0, 1], dtype=np.complex128), atol=1e-10)

    def test_rx_rotation(self):
        circuit = QuantumCircuit(1)
        circuit.rx(0, np.pi)
        state = circuit.statevector()
        expected = np.array([0, -1j], dtype=np.complex128)
        np.testing.assert_allclose(np.abs(state), np.abs(expected), atol=1e-10)

    def test_ry_rotation(self):
        circuit = QuantumCircuit(1)
        circuit.ry(0, np.pi)
        state = circuit.statevector()
        np.testing.assert_allclose(state, np.array([0, 1], dtype=np.complex128), atol=1e-10)

    def test_measurement_counts(self):
        np.random.seed(42)
        circuit = QuantumCircuit(1)
        circuit.h(0)
        counts = circuit.measure(shots=20000)
        assert sum(counts.values()) == 20000
        assert "0" in counts
        assert "1" in counts
        assert 3000 <= counts["0"] <= 17000
        assert 3000 <= counts["1"] <= 17000

    def test_circuit_reset(self):
        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.reset()
        state = circuit.statevector()
        np.testing.assert_allclose(state, np.array([1, 0], dtype=np.complex128), atol=1e-10)

    def test_multi_qubit_bell_state(self):
        circuit = QuantumCircuit(2)
        circuit.h(0).cx(0, 1)
        state = circuit.statevector()
        expected = np.array([1, 0, 0, 1], dtype=np.complex128) / np.sqrt(2)
        np.testing.assert_allclose(np.abs(state), np.abs(expected), atol=1e-10)

    def test_state_norm_preserved(self):
        circuit = QuantumCircuit(3)
        circuit.h(0).h(1).h(2)
        for i in range(3):
            circuit.ry(i, np.pi / 4)
        state = circuit.statevector()
        assert abs(np.linalg.norm(state) - 1.0) < 1e-10


class TestGateDecomposer:
    def test_decompose_rotation(self):
        rx, ry, rz = GateDecomposer.decompose_rotation(np.pi / 3)
        assert rx.shape == (2, 2)
        assert ry.shape == (2, 2)
        assert rz.shape == (2, 2)

    def test_cz_gate(self):
        cz = GateDecomposer.cz()
        assert cz.shape == (4, 4)
        assert np.allclose(np.diag(cz), [1, 1, 1, -1])

    def test_swap_gate(self):
        swap = GateDecomposer.swap()
        assert swap.shape == (4, 4)
        expected = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
        np.testing.assert_allclose(swap, expected, atol=1e-10)
