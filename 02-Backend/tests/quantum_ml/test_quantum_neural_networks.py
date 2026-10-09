import numpy as np
from quantum_ml.quantum_circuits import QuantumCircuit
from quantum_ml.quantum_neural_networks import ParameterizedQuantumCircuit


class TestParameterizedQuantumCircuit:
    def test_forward_output_shape(self):
        pqc = ParameterizedQuantumCircuit(num_qubits=3, num_layers=2)
        x = np.random.randn(3)
        probs = pqc.forward(x)
        assert probs.shape == (8,)

    def test_forward_probability_sum(self):
        pqc = ParameterizedQuantumCircuit(num_qubits=2, num_layers=2)
        x = np.random.randn(2)
        probs = pqc.forward(x)
        assert abs(np.sum(probs) - 1.0) < 1e-10

    def test_gradient_shape(self):
        pqc = ParameterizedQuantumCircuit(num_qubits=2, num_layers=2)
        x = np.random.randn(2)
        grad = pqc.gradient(x)
        assert grad.shape == pqc.params.shape

    def test_loss_non_negative(self):
        pqc = ParameterizedQuantumCircuit(num_qubits=2, num_layers=2)
        x = np.random.randn(2)
        loss = pqc.loss(x, 1.0)
        assert loss >= 0

    def test_train_step_reduces_loss(self):
        np.random.seed(42)
        pqc = ParameterizedQuantumCircuit(num_qubits=2, num_layers=2)
        x = np.random.randn(2)
        initial_loss = pqc.loss(x, 1.0)
        for _ in range(200):
            pqc.train_step(x, 1.0, lr=0.01)
        final_loss = pqc.loss(x, 1.0)
        assert final_loss <= initial_loss

    def test_measure_expectation(self):
        np.random.seed(42)
        pqc = ParameterizedQuantumCircuit(num_qubits=2, num_layers=2)
        x = np.random.randn(2)
        observable = np.eye(4)
        exp = pqc.measure_expectation(x, observable)
        assert abs(exp - 1.0) < 0.5

    def test_forward_with_custom_params(self):
        pqc = ParameterizedQuantumCircuit(num_qubits=2, num_layers=2)
        x = np.random.randn(2)
        params = np.random.randn(pqc.num_params)
        probs = pqc.forward(x, params)
        assert probs.shape == (4,)
        assert abs(np.sum(probs) - 1.0) < 1e-10


class TestParameterizedQuantumCircuitMethods:
    def test_circuit_returns_quantum_circuit(self):
        pqc = ParameterizedQuantumCircuit(num_qubits=2, num_layers=2)
        x = np.random.randn(2)
        params = np.random.randn(pqc.num_params)
        circuit = pqc.circuit(x, params)
        assert isinstance(circuit, QuantumCircuit)
        assert circuit.num_qubits == 2

    def test_circuit_num_qubits(self):
        pqc = ParameterizedQuantumCircuit(num_qubits=3, num_layers=2)
        x = np.random.randn(3)
        params = np.random.randn(pqc.num_params)
        circuit = pqc.circuit(x, params)
        assert circuit.num_qubits == 3
