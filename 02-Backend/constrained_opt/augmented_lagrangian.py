import numpy as np


def augmented_lagrangian(f, grad_f, constraints, x0, lr=1e-2, mu=1.0, mu_inc=2.0, max_iter=100, tol=1e-6):
    """Augmented Lagrangian method for equality constraints c_i(x) = 0."""
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
            g += lambdas[i] * grad_c + mu * ci * grad_c
            lambdas[i] += mu * ci
        x = x - lr * g
        if np.linalg.norm(g) < tol:
            break
    return x
