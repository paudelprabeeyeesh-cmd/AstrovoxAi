import numpy as np


def cma_es_wrapper(
    f,
    x0,
    sigma=1.0,
    pop_size=20,
    max_iter=100,
    tol=1e-6,
    bounds=None,
):
    x = np.copy(x0)
    n = len(x)
    step_size = sigma
    for _ in range(max_iter):
        solutions = np.array([x + step_size * np.random.randn(n) for _ in range(pop_size)])
        if bounds is not None:
            for i in range(pop_size):
                for d in range(n):
                    solutions[i][d] = np.clip(solutions[i][d], bounds[d][0], bounds[d][1])
        fitness = np.array([f(s) for s in solutions])
        idx = np.argsort(fitness)
        mu = max(1, pop_size // 4)
        parents = solutions[idx[:mu]]
        x_new = np.mean(parents, axis=0)
        if bounds is not None:
            for d in range(n):
                x_new[d] = np.clip(x_new[d], bounds[d][0], bounds[d][1])
        if np.linalg.norm(x_new - x) < tol:
            x = x_new
            break
        step_size *= 0.9
        x = x_new
    return x
