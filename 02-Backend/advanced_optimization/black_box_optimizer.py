import numpy as np


def powell_method(f, x0, max_iter=100, tol=1e-6):
    x = np.copy(x0)
    n = len(x)
    directions = np.eye(n)
    for _ in range(max_iter):
        x_old = np.copy(x)
        for i in range(n):
            alpha = 0.0
            for _ in range(50):
                e = 1e-5
                grad = np.zeros(n)
                for j in range(n):
                    ej = np.zeros(n)
                    ej[j] = e
                    grad[j] = (f(x + directions[i] * (alpha + e)) - f(x + directions[i] * (alpha - e))) / (2 * e)
                alpha = alpha - 1e-2 * np.dot(grad, directions[i])
            x = x + alpha * directions[i]
        if np.linalg.norm(x - x_old) < tol:
            break
        new_dir = x - x_old
        directions = np.vstack([directions[1:], new_dir.reshape(1, -1)])
    return x


def cma_es_simple(f, x0, sigma=1.0, pop_size=20, max_iter=100):
    x = np.copy(x0)
    n = len(x)
    for _ in range(max_iter):
        solutions = np.array([x + sigma * np.random.randn(n) for _ in range(pop_size)])
        fitness = np.array([f(s) for s in solutions])
        idx = np.argsort(fitness)
        mu = pop_size // 4
        parents = solutions[idx[:mu]]
        x = np.mean(parents, axis=0)
        sigma *= 0.9
    return x


def random_search(f, bounds, max_iter=200):
    dim = len(bounds)
    best_x = np.array([np.random.uniform(b[0], b[1]) for b in bounds])
    best_f = f(best_x)
    for _ in range(max_iter):
        x = np.array([np.random.uniform(b[0], b[1]) for b in bounds])
        y = f(x)
        if y < best_f:
            best_f = y
            best_x = x
    return best_x
