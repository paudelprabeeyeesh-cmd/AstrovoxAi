import numpy as np


def penalty_method(f, grad_f, constraints, x0, penalty=1.0, growth=2.0, lr=1e-2, max_iter=100, tol=1e-6):
    """Penalty method for inequality constraints c_i(x) <= 0."""
    x = np.copy(x0)
    for _ in range(max_iter):
        g = np.copy(grad_f(x))
        for c in constraints:
            ci = c(x)
            if ci > 0:
                h = 1e-5
                grad_c = np.zeros_like(x)
                for i in range(len(x)):
                    e = np.zeros_like(x)
                    e[i] = h
                    grad_c[i] = (c(x + e) - c(x - e)) / (2 * h)
                g += penalty * ci * grad_c
        x = x - lr * g
        penalty *= growth
        if np.linalg.norm(g) < tol:
            break
    return x
