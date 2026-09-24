import numpy as np


def qaoa_layer(params, cost_mat, mixer_mat, depth):
    n = cost_mat.shape[0]
    state = np.eye(2 ** n, dtype=complex)[0]
    for d in range(depth):
        gamma = params[2 * d]
        beta = params[2 * d + 1]
        exp_cost = np.eye(2 ** n, dtype=complex)
        for i in range(2 ** n):
            bits = [(i >> j) & 1 for j in range(n)]
            cost = sum(cost_mat[j, k] * bits[j] * bits[k] for j in range(n) for k in range(n))
            exp_cost[i, i] = np.exp(-1j * gamma * cost)
        exp_mixer = np.eye(2 ** n, dtype=complex)
        for i in range(2 ** n):
            exp_mixer[i, i] = np.exp(-1j * beta * mixer_mat[i, i])
        state = exp_mixer @ exp_cost @ state
    probs = np.abs(state) ** 2
    return probs


def simulated_quantum_annealing(f, x0, T_init=1.0, T_final=1e-4, steps=1000):
    x = np.copy(x0)
    current = f(x)
    T = T_init
    for t in range(steps):
        T = T_init * ((T_final / T_init) ** (t / steps))
        delta_x = np.random.randn(*x.shape) * 0.1
        x_new = x + delta_x
        new = f(x_new)
        if new < current or np.random.rand() < np.exp(-(new - current) / T):
            x = x_new
            current = new
    return x


def quantum_inspired_population(f, bounds, pop_size=20, max_iter=100):
    dim = len(bounds)
    pop = np.array([np.random.uniform(b[0], b[1], dim) for _ in range(pop_size)])
    fitness = np.array([f(ind) for ind in pop])
    for _ in range(max_iter):
        for i in range(pop_size):
            j = np.random.randint(0, pop_size)
            k = np.random.randint(0, pop_size)
            while j == i:
                j = np.random.randint(0, pop_size)
            while k == i or k == j:
                k = np.random.randint(0, pop_size)
            mutant = pop[i] + 0.5 * (pop[j] - pop[k])
            mutant = np.clip(mutant, [b[0] for b in bounds], [b[1] for b in bounds])
            f_mut = f(mutant)
            if f_mut < fitness[i]:
                pop[i] = mutant
                fitness[i] = f_mut
    best_idx = np.argmin(fitness)
    return pop[best_idx]
