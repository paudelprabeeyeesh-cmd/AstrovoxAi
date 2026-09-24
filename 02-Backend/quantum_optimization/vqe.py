import cmath
import math
import random


def _kron(A, B):
    rows = len(A)
    cols = len(A[0])
    brows = len(B)
    bcols = len(B[0])
    result = [[0j] * (cols * bcols) for _ in range(rows * brows)]
    for i in range(rows):
        for j in range(cols):
            for k in range(brows):
                for l in range(bcols):
                    result[i * brows + k][j * bcols + l] = A[i][j] * B[k][l]
    return result


def _apply_single_qubit(state, gate, target, num_qubits):
    dim = len(state)
    new_state = [0j] * dim
    for i in range(dim):
        c = (i >> target) & 1
        e = i & ~(1 << target)
        new_state[e] += gate[0][c] * state[i]
        new_state[e | (1 << target)] += gate[1][c] * state[i]
    return new_state


def _apply_cnot(state, control, target, num_qubits):
    dim = len(state)
    new_state = [0j] * dim
    for i in range(dim):
        c = (i >> control) & 1
        t = (i >> target) & 1
        e = i & ~(1 << control) & ~(1 << target)
        if c == 1:
            t ^= 1
        new_state[e | (c << control) | (t << target)] += state[i]
    return new_state


def _expectation(state, operator):
    dim = len(state)
    result = [0j] * dim
    for r in range(dim):
        s = 0j
        for c in range(dim):
            s += operator[r][c] * state[c]
        result[r] = s
    energy = 0j
    for i in range(dim):
        energy += state[i].conjugate() * result[i]
    return energy.real


def _ry(theta):
    return [
        [cmath.exp(-1j * theta / 2), 0],
        [0, cmath.exp(1j * theta / 2)],
    ]


def _rx(theta):
    return [
        [cmath.cos(theta / 2), -1j * cmath.sin(theta / 2)],
        [-1j * cmath.sin(theta / 2), cmath.cos(theta / 2)],
    ]


def _initialize_state(num_qubits):
    dim = 1 << num_qubits
    state = [0j] * dim
    state[0] = 1.0 + 0j
    return state


class VQE:
    def __init__(self, num_qubits, ansatz_depth=3):
        self.num_qubits = num_qubits
        self.ansatz_depth = ansatz_depth
        self.parameters = [random.gauss(0, 0.1) for _ in range(ansatz_depth * num_qubits)]
        self.hamiltonian = self._default_hamiltonian()

    def _default_hamiltonian(self):
        dim = 1 << self.num_qubits
        h = [[0j] * dim for _ in range(dim)]
        for i in range(self.num_qubits):
            z_op = [[1 + 0j]]
            for j in range(self.num_qubits):
                if j == i:
                    z_op = _kron(z_op, [[1, 0], [0, -1]])
                else:
                    z_op = _kron(z_op, [[1, 0], [0, 1]])
            for r in range(dim):
                for c in range(dim):
                    h[r][c] += z_op[r][c]
        for i in range(self.num_qubits - 1):
            zz_op = [[1 + 0j]]
            for j in range(self.num_qubits):
                if j == i or j == i + 1:
                    zz_op = _kron(zz_op, [[1, 0], [0, -1]])
                else:
                    zz_op = _kron(zz_op, [[1, 0], [0, 1]])
            for r in range(dim):
                for c in range(dim):
                    h[r][c] += zz_op[r][c]
        return h

    def ansatz(self, params):
        state = _initialize_state(self.num_qubits)
        for d in range(self.ansatz_depth):
            for i in range(self.num_qubits):
                state = _apply_single_qubit(state, _ry(params[d * self.num_qubits + i]), i, self.num_qubits)
            for i in range(0, self.num_qubits - 1, 2):
                state = _apply_cnot(state, i, i + 1, self.num_qubits)
            for i in range(1, self.num_qubits - 1, 2):
                state = _apply_cnot(state, i, i + 1, self.num_qubits)
        return state

    def energy(self, params):
        state = self.ansatz(params)
        return _expectation(state, self.hamiltonian)

    def optimize(self, max_iter=100, lr=0.01):
        params = list(self.parameters)
        best_params = list(params)
        best_energy = self.energy(params)
        for _ in range(max_iter):
            grad = self._gradient(params)
            for i in range(len(params)):
                params[i] -= lr * grad[i]
            e = self.energy(params)
            if e < best_energy:
                best_energy = e
                best_params = list(params)
        self.parameters = best_params
        return best_params, best_energy

    def _gradient(self, params, epsilon=1e-5):
        grad = [0.0] * len(params)
        base = self.energy(params)
        for i in range(len(params)):
            shifted = list(params)
            shifted[i] += epsilon
            grad[i] = (self.energy(shifted) - base) / epsilon
        return grad
