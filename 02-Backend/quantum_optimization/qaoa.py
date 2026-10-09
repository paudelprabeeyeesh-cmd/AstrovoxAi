import cmath
import math


def qaoa_layer(params, cost_mat, mixer_mat, depth):
    n = len(cost_mat)
    dim = 1 << n
    state = [0j] * dim
    state[0] = 1.0 + 0j

    for d in range(depth):
        gamma = params[2 * d]
        beta = params[2 * d + 1]

        new_state = [0j] * dim
        for i in range(dim):
            bits = [(i >> j) & 1 for j in range(n)]
            cost = sum(cost_mat[j][k] * bits[j] * bits[k] for j in range(n) for k in range(n))
            phase = cmath.exp(-1j * gamma * cost)
            new_state[i] = phase * state[i]
        state = new_state

        new_state = [0j] * dim
        for i in range(dim):
            phase = cmath.exp(-1j * beta * mixer_mat[i][i])
            new_state[i] = phase * state[i]
        state = new_state

    probs = [abs(z) ** 2 for z in state]
    total = sum(probs)
    if total > 0:
        probs = [p / total for p in probs]
    return probs
