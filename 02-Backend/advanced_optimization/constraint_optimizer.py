import numpy as np


def sqp(f, grad_f, constraints, x0, lr=1e-2, max_iter=200, tol=1e-6):
    x = np.copy(x0)
    for _ in range(max_iter):
        g = grad_f(x)
        H = np.eye(len(x))
        for c in constraints:
            ci = c(x)
            if ci > 0:
                h = 1e-5
                grad_c = np.zeros_like(x)
                for j in range(len(x)):
                    e = np.zeros_like(x)
                    e[j] = h
                    grad_c[j] = (c(x + e) - c(x - e)) / (2 * h)
                g += 10.0 * ci * grad_c
                H += 10.0 * np.outer(grad_c, grad_c)
        try:
            step = np.linalg.solve(H + 1e-6 * np.eye(len(x)), -g)
        except np.linalg.LinAlgError:
            step = -lr * g
        x_new = x + lr * step
        if np.linalg.norm(x_new - x) < tol:
            break
        x = x_new
    return x


def interior_point(f, grad_f, constraint, x0, t=1.0, t_growth=2.0, lr=1e-2, max_iter=200):
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
    return x


def active_set(f, grad_f, constraints, x0, lr=1e-2, max_iter=200, tol=1e-6):
    x = np.copy(x0)
    active = []
    for _ in range(max_iter):
        g = grad_f(x)
        for c in constraints:
            ci = c(x)
            if abs(ci) < 1e-4:
                active.append(c)
        for c in active:
            ci = c(x)
            h = 1e-5
            grad_c = np.zeros_like(x)
            for j in range(len(x)):
                e = np.zeros_like(x)
                e[j] = h
                grad_c[j] = (c(x + e) - c(x - e)) / (2 * h)
            g += 5.0 * ci * grad_c
        x_new = x - lr * g
        if np.linalg.norm(x_new - x) < tol:
            break
        x = x_new
    return x
