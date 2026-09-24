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


def augmented_lagrangian(f, grad_f, constraints, x0, lr=1e-2, mu=1.0, mu_inc=10.0, max_iter=100):
    x = np.copy(x0)
    lambdas = np.zeros(len(constraints))
    for _ in range(max_iter):
        def penalty(x):
            val = f(x)
            for i, c in enumerate(constraints):
                val += lambdas[i] * c(x) + 0.5 * mu * max(c(x), 0.0) ** 2
            return val
        def penalty_grad(x):
            g = grad_f(x)
            for i, c in enumerate(constraints):
                ci = c(x)
                g += lambdas[i] * (1.0 if ci >= 0 else 0.0) * np.array(np.gradient(ci)) if np.isscalar(ci) else lambdas[i] * np.gradient(ci)
                g += mu * max(ci, 0.0) * np.gradient(ci) if np.isscalar(ci) else mu * max(ci, 0.0) * np.gradient(ci)
            return g
        g = grad_f(x)
        for i, c in enumerate(constraints):
            ci = c(x)
            if ci > 0:
                lambdas[i] += mu * ci
        x = x - lr * g
    return x


def penalty_method(f, grad_f, constraints, x0, penalty=1.0, growth=10.0, lr=1e-2, max_iter=100):
    x = np.copy(x0)
    for _ in range(max_iter):
        def penalized(x):
            val = f(x)
            for c in constraints:
                val += 0.5 * penalty * max(c(x), 0.0) ** 2
            return val
        g = grad_f(x)
        for c in constraints:
            ci = c(x)
            if ci > 0:
                g += penalty * ci * np.gradient(ci) if np.isscalar(ci) else penalty * ci * np.gradient(ci)
        x = x - lr * g
        penalty *= growth
    return x


def barrier_method(f, grad_f, constraint, x0, t=1.0, t_growth=10.0, lr=1e-2, max_iter=100):
    x = np.copy(x0)
    for _ in range(max_iter):
        def barrier(x):
            return f(x) - (1.0 / t) * np.log(-constraint(x))
        g = grad_f(x)
        ci = constraint(x)
        g += (1.0 / (t * (-ci))) * np.gradient(ci) if np.isscalar(ci) else (1.0 / (t * (-ci))) * np.gradient(ci)
        x = x - lr * g
        t *= t_growth
    return x
