import numpy as np
import pytest
from quantum_ml.quantum_feature_map import FeatureMap, ZZFeatureMap, PauliFeatureMap


class TestFeatureMap:
    def test_zz_encode_returns_circuit(self):
        fmap = ZZFeatureMap(4)
        x = np.random.randn(3)
        circuit = fmap.encode(x)
        assert isinstance(circuit, object)

    def test_pauli_encode_returns_circuit(self):
        fmap = PauliFeatureMap(3)
        x = np.random.randn(4)
        circuit = fmap.encode(x)
        assert isinstance(circuit, object)

    def test_zz_state_norm(self):
        fmap = ZZFeatureMap(3)
        x = np.array([0.5, -0.3, 1.2])
        circuit = fmap.encode(x)
        state = circuit.run()
        probs = np.abs(state) ** 2
        np.testing.assert_allclose(np.sum(probs), 1.0, atol=1e-10)

    def test_pauli_state_norm(self):
        fmap = PauliFeatureMap(3)
        x = np.array([0.1, 0.2, 0.3])
        circuit = fmap.encode(x)
        state = circuit.run()
        probs = np.abs(state) ** 2
        np.testing.assert_allclose(np.sum(probs), 1.0, atol=1e-10)

    def test_zz_same_input_same_output(self):
        fmap = ZZFeatureMap(2)
        x = np.array([0.5, 0.5])
        state1 = fmap.encode(x).run()
        state2 = fmap.encode(x).run()
        np.testing.assert_allclose(state1, state2, atol=1e-10)

    def test_pauli_same_input_same_output(self):
        fmap = PauliFeatureMap(2)
        x = np.array([0.5, 0.5])
        state1 = fmap.encode(x).run()
        state2 = fmap.encode(x).run()
        np.testing.assert_allclose(state1, state2, atol=1e-10)

    def test_zz_different_inputs(self):
        fmap = ZZFeatureMap(2)
        x1 = np.array([0.0, 0.0])
        x2 = np.array([np.pi, np.pi])
        s1 = fmap.encode(x1).run()
        s2 = fmap.encode(x2).run()
        assert not np.allclose(s1, s2)

    def test_pauli_different_inputs(self):
        fmap = PauliFeatureMap(2)
        x1 = np.array([0.0, 0.0])
        x2 = np.array([np.pi, np.pi])
        s1 = fmap.encode(x1).run()
        s2 = fmap.encode(x2).run()
        assert not np.allclose(s1, s2)

    def test_feature_map_num_qubits(self):
        fmap = ZZFeatureMap(5)
        assert fmap.num_qubits == 5
        fmap2 = PauliFeatureMap(4)
        assert fmap2.num_qubits == 4
