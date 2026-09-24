import numpy as np


def barrier_method(f, grad_f, constraint, x0, t=1.0, t_growth=2.0, lr=1e-2, max_iter=100, tol=1e-6):
    """Barrier method for inequality constraint c(x) <= 0."""
    x = np.copy(x0)
    for _ in range(max_iter):
        ci = constraint(x)
        if ci >= 0:
            break
        h = 1e-5
        grad_c = np.zeros_like(x)
        for i in range(len(x)):
            e = np.zeros_like(x)
            e[i] = h
            grad_c[i] = (constraint(x + e) - constraint(x - e)) / (2 * h)
        g = grad_f(x) - (1.0 / (t * (-ci))) * grad_c
        x = x - lr * g
        t *= t_growth
        if np.linalg.norm(g) < tol:
            break
    return x
