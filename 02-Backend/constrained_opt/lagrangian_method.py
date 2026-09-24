import numpy as np


def lagrangian_method(f, grad_f, constraints, x0, lr=1e-2, max_iter=100, tol=1e-6):
    """Method of Lagrange multipliers for equality constraints c_i(x) = 0."""
    x = np.copy(x0)
    lambdas = np.zeros(len(constraints))
    for _ in range(max_iter):
        g = np.copy(grad_f(x))
        for i, c in enumerate(constraints):
            ci = c(x)
            h = 1e-5
            grad_c = np.zeros_like(x)
            for j in range(len(x)):
                e = np.zeros_like(x)
                e[j] = h
                grad_c[j] = (c(x + e) - c(x - e)) / (2 * h)
            g += lambdas[i] * grad_c
            lambdas[i] += lr * ci
        x = x - lr * g
        if np.linalg.norm(g) < tol:
            break
    return x
