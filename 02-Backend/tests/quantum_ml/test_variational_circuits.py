import numpy as np
from quantum_ml.variational_circuits import VQE, QAOA, AnsatzDesigner


class TestVQE:
    def test_energy_positive(self):
        vqe = VQE(num_qubits=2, ansatz_depth=2)
        params = np.random.randn(4)
        energy = vqe.energy(params)
        assert isinstance(energy, float)
        assert not np.isnan(energy)

    def test_optimize_returns_best(self):
        vqe = VQE(num_qubits=2, ansatz_depth=2)
        best_params, best_energy = vqe.optimize(max_iter=10, lr=0.01)
        assert len(best_params) == 4
        assert isinstance(best_energy, float)

    def test_ansatz_shape(self):
        vqe = VQE(num_qubits=3, ansatz_depth=2)
        params = np.random.randn(6)
        circuit = vqe.ansatz(params)
        assert circuit.num_qubits == 3

    def test_default_hamiltonian_shape(self):
        vqe = VQE(num_qubits=2)
        assert vqe.hamiltonian.shape == (4, 4)


class TestQAOA:
    def test_expectation(self):
        qaoa = QAOA(num_qubits=3, p=2)
        params = np.random.rand(4) * np.pi / 2
        exp = qaoa.expectation(params)
        assert isinstance(exp, float)

    def test_optimize_returns_best(self):
        qaoa = QAOA(num_qubits=3, p=2)
        best_params, best_val = qaoa.optimize(max_iter=10, lr=0.01)
        assert len(best_params) == 4

    def test_circuit_creation(self):
        qaoa = QAOA(num_qubits=3, p=1)
        params = np.random.rand(2) * np.pi / 2
        circuit = qaoa.circuit(params)
        assert circuit.num_qubits == 3


class TestAnsatzDesigner:
    def test_hardware_efficient(self):
        gates = AnsatzDesigner.hardware_efficient(3, 2)
        assert len(gates) > 0
        assert all(len(g) == 3 for g in gates)

    def test_strongly_entangling(self):
        gates = AnsatzDesigner.strongly_entangling(3, 2)
        assert len(gates) > 0

    def test_hardware_efficient_gate_types(self):
        gates = AnsatzDesigner.hardware_efficient(2, 1)
        gate_types = [g[0] for g in gates]
        assert "ry" in gate_types
        assert "rz" in gate_types
        assert "cx" in gate_types


class TestVQEMethods:
    def test_gradient_shape(self):
        vqe = VQE(num_qubits=2, ansatz_depth=2)
        params = np.random.randn(4)
        grad = vqe._gradient(params)
        assert grad.shape == params.shape

    def test_problem_hamiltonian_shape(self):
        qaoa = QAOA(num_qubits=3, p=1)
        h = qaoa._problem_hamiltonian()
        assert h.shape == (8, 8)

    def test_mixer_hamiltonian_length(self):
        qaoa = QAOA(num_qubits=3, p=1)
        mixers = qaoa._mixer_hamiltonian()
        assert len(mixers) == 3

    def test_param_gradient_shape(self):
        qaoa = QAOA(num_qubits=3, p=1)
        params = np.random.rand(2) * np.pi / 2
        grad = qaoa._param_gradient(params)
        assert grad.shape == params.shape
