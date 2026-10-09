import numpy as np


def projected_gradient_descent(f, grad_f, proj, x0, lr=1e-2, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    for _ in range(max_iter):
        g = grad_f(x)
        x_new = proj(x - lr * g)
        if np.linalg.norm(x_new - x) < tol:
            break
        x = x_new
    return x


def augmented_lagrangian(f, grad_f, constraints, x0, lr=1e-2, mu=1.0, mu_inc=2.0, max_iter=100):
    x = np.copy(x0)
    lambdas = np.zeros(len(constraints))
    for _ in range(max_iter):
        g = grad_f(x)
        for i, c in enumerate(constraints):
            ci = c(x)
            if ci > 0:
                lambdas[i] += mu * ci
                h = 1e-5
                grad_c = np.zeros_like(x)
                for j in range(len(x)):
                    e = np.zeros_like(x)
                    e[j] = h
                    grad_c[j] = (c(x + e) - c(x - e)) / (2 * h)
                g += lambdas[i] * grad_c + mu * ci * grad_c
        x = x - lr * g
    return x


def penalty_method(f, grad_f, constraints, x0, penalty=1.0, growth=2.0, lr=1e-2, max_iter=100):
    x = np.copy(x0)
    for _ in range(max_iter):
        g = grad_f(x)
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
    return x


def barrier_method(f, grad_f, constraint, x0, t=1.0, t_growth=2.0, lr=1e-2, max_iter=100):
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
