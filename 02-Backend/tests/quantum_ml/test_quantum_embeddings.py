import numpy as np
from quantum_ml.quantum_embeddings import QuantumEmbedding
from quantum_ml.quantum_circuits import QuantumCircuit


class TestQuantumEmbeddings:
    def test_amplitude_encode_normalization(self):
        data = np.array([1.0, 2.0, 3.0, 4.0])
        embedded = QuantumEmbedding.amplitude_encode(data)
        assert abs(np.linalg.norm(embedded) - 1.0) < 1e-10

    def test_amplitude_encode_zero(self):
        data = np.array([0.0, 0.0, 0.0])
        embedded = QuantumEmbedding.amplitude_encode(data)
        np.testing.assert_allclose(embedded, np.zeros(3), atol=1e-10)

    def test_angle_encode_shape(self):
        data = np.array([0.1, 0.5, 0.9, 0.3])
        angles = QuantumEmbedding.angle_encode(data)
        assert len(angles) == 4

    def test_basis_encode(self):
        data = np.array([1.0, -1.0, 0.5, -0.5])
        bits = QuantumEmbedding.basis_encode(data)
        assert bits == [1, 0, 1, 0]

    def test_phase_encode_shape(self):
        data = np.array([1.0, 2.0, 3.0])
        phases = QuantumEmbedding.phase_encode(data)
        assert len(phases) == 3

    def test_iqp_encode_circuit(self):
        features = np.array([0.1, 0.5, 0.9])
        circuit = QuantumEmbedding.iqp_encode(features)
        assert isinstance(circuit, QuantumCircuit)
        assert circuit.num_qubits == 3

    def test_iqp_encode_state_norm(self):
        features = np.array([0.1, 0.5, 0.9])
        circuit = QuantumEmbedding.iqp_encode(features)
        state = circuit.statevector()
        assert abs(np.linalg.norm(state) - 1.0) < 1e-10

    def test_amplitude_embedding(self):
        circuit = QuantumCircuit(2)
        data = np.array([1.0, 0.5, 0.5, 1.0])
        result = QuantumEmbedding.amplitude_embedding(circuit, data)
        assert result is circuit
        expected_norm = np.linalg.norm(data / (np.linalg.norm(data) + 1e-10))
        actual_norm = np.linalg.norm(result.state)
        assert abs(actual_norm - expected_norm) < 1e-10
