import numpy as np
from typing import List, Tuple, Optional
from .quantum_circuits import QuantumCircuit


class VQE:
    def __init__(self, num_qubits: int, ansatz_depth: int = 3):
        self.num_qubits = num_qubits
        self.ansatz_depth = ansatz_depth
        self.parameters = np.random.randn(ansatz_depth * num_qubits) * 0.1
        self.hamiltonian = self._default_hamiltonian()

    def _default_hamiltonian(self) -> np.ndarray:
        dim = 2**self.num_qubits
        h = np.zeros((dim, dim), dtype=np.complex128)
        for i in range(self.num_qubits):
            z_op = np.eye(1, dtype=np.complex128)
            for j in range(self.num_qubits):
                if j == i:
                    z_op = np.kron(z_op, np.array([[1, 0], [0, -1]], dtype=np.complex128))
                else:
                    z_op = np.kron(z_op, np.eye(2, dtype=np.complex128))
            h += z_op
        for i in range(self.num_qubits - 1):
            zz_op = np.eye(1, dtype=np.complex128)
            for j in range(self.num_qubits):
                if j == i:
                    zz_op = np.kron(zz_op, np.array([[1, 0], [0, -1]], dtype=np.complex128))
                elif j == i + 1:
                    zz_op = np.kron(zz_op, np.array([[1, 0], [0, -1]], dtype=np.complex128))
                else:
                    zz_op = np.kron(zz_op, np.eye(2, dtype=np.complex128))
            h += zz_op
        return h

    def ansatz(self, params: np.ndarray) -> QuantumCircuit:
        circuit = QuantumCircuit(self.num_qubits)
        for i in range(self.num_qubits):
            circuit.h(i)
        for d in range(self.ansatz_depth):
            for i in range(self.num_qubits):
                circuit.ry(i, params[d * self.num_qubits + i])
            for i in range(0, self.num_qubits - 1, 2):
                circuit.cnot(i, i + 1)
            for i in range(1, self.num_qubits - 1, 2):
                circuit.cnot(i, i + 1)
        return circuit

    def energy(self, params: np.ndarray) -> float:
        circuit = self.ansatz(params)
        state = circuit.run()
        energy = np.real(np.conj(state) @ self.hamiltonian @ state)
        return float(energy)

    def optimize(self, max_iter: int = 100, lr: float = 0.01) -> Tuple[np.ndarray, float]:
        params = self.parameters.copy()
        best_params = params.copy()
        best_energy = self.energy(params)
        for _ in range(max_iter):
            grad = self._gradient(params)
            params = params - lr * grad
            energy = self.energy(params)
            if energy < best_energy:
                best_energy = energy
                best_params = params.copy()
        self.parameters = best_params
        return best_params, best_energy

    def _gradient(self, params: np.ndarray, epsilon: float = 1e-5) -> np.ndarray:
        grad = np.zeros_like(params)
        base = self.energy(params)
        for i in range(len(params)):
            shifted = params.copy()
            shifted[i] += epsilon
            grad[i] = (self.energy(shifted) - base) / epsilon
        return grad


class QAOA:
    def __init__(self, num_qubits: int, p: int = 1):
        self.num_qubits = num_qubits
        self.p = p
        self.parameters = np.random.rand(2 * p) * np.pi / 2

    def _problem_hamiltonian(self) -> np.ndarray:
        dim = 2**self.num_qubits
        h = np.zeros((dim, dim), dtype=np.complex128)
        for i in range(self.num_qubits):
            z_op = np.eye(1, dtype=np.complex128)
            for j in range(self.num_qubits):
                if j == i:
                    z_op = np.kron(z_op, np.array([[1, 0], [0, -1]], dtype=np.complex128))
                else:
                    z_op = np.kron(z_op, np.eye(2, dtype=np.complex128))
            h += -z_op
        return h

    def _mixer_hamiltonian(self) -> List[np.ndarray]:
        mixers = []
        for i in range(self.num_qubits):
            x_op = np.eye(1, dtype=np.complex128)
            for j in range(self.num_qubits):
                if j == i:
                    x_op = np.kron(x_op, np.array([[0, 1], [1, 0]], dtype=np.complex128))
                else:
                    x_op = np.kron(x_op, np.eye(2, dtype=np.complex128))
            mixers.append(x_op)
        return mixers

    def circuit(self, params: np.ndarray) -> QuantumCircuit:
        circuit = QuantumCircuit(self.num_qubits)
        for i in range(self.num_qubits):
            circuit.h(i)
        for k in range(self.p):
            gamma, beta = params[2 * k], params[2 * k + 1]
            problem_h = self._problem_hamiltonian()
            state = circuit.run()
            phase = np.exp(-1j * gamma * np.real(np.conj(state) @ problem_h @ state))
            circuit.state = circuit.state * phase
            for i in range(self.num_qubits):
                circuit.rx(i, 2 * beta)
        return circuit

    def expectation(self, params: np.ndarray) -> float:
        circuit = self.circuit(params)
        state = circuit.run()
        h = self._problem_hamiltonian()
        return float(np.real(np.conj(state) @ h @ state))

    def optimize(self, max_iter: int = 50, lr: float = 0.01) -> Tuple[np.ndarray, float]:
        params = self.parameters.copy()
        best = params.copy()
        best_val = self.expectation(params)
        for _ in range(max_iter):
            grad = self._param_gradient(params)
            params = params - lr * grad
            val = self.expectation(params)
            if val < best_val:
                best_val = val
                best = params.copy()
        self.parameters = best
        return best, best_val

    def _param_gradient(self, params: np.ndarray, eps: float = 1e-5) -> np.ndarray:
        grad = np.zeros_like(params)
        base = self.expectation(params)
        for i in range(len(params)):
            p = params.copy()
            p[i] += eps
            grad[i] = (self.expectation(p) - base) / eps
        return grad


class AnsatzDesigner:
    @staticmethod
    def hardware_efficient(num_qubits: int, depth: int) -> List[Tuple[str, List[int], Optional[float]]]:
        gates = []
        for d in range(depth):
            for i in range(num_qubits):
                gates.append(("ry", [i], d * 0.1 + i * 0.1))
                gates.append(("rz", [i], d * 0.2 + i * 0.2))
            for i in range(0, num_qubits - 1, 2):
                gates.append(("cx", [i, i + 1], None))
            for i in range(1, num_qubits - 1, 2):
                gates.append(("cx", [i, i + 1], None))
        return gates

    @staticmethod
    def strongly_entangling(num_qubits: int, depth: int) -> List[Tuple[str, List[int], Optional[float]]]:
        gates = []
        for d in range(depth):
            for i in range(num_qubits):
                gates.append(("rz", [i], d * 0.3 + i * 0.5))
                gates.append(("ry", [i], d * 0.2 + i * 0.4))
                gates.append(("rz", [i], d * 0.3 + i * 0.5))
            for i in range(num_qubits):
                gates.append(("cx", [i, (i + 1) % num_qubits], None))
        return gates
