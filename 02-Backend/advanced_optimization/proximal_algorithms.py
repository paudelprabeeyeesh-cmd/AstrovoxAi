import numpy as np


def proximal_gradient(f, grad_f, prox, x0, lr=1e-2, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    for _ in range(max_iter):
        g = grad_f(x)
        x_new = prox(x - lr * g, lr)
        if np.linalg.norm(x_new - x) < tol:
            break
        x = x_new
    return x


def ista(f, grad_f, prox, x0, lr=1e-2, max_iter=1000):
    x = np.copy(x0)
    for _ in range(max_iter):
        g = grad_f(x)
        x = prox(x - lr * g, lr)
    return x


def fista(f, grad_f, prox, x0, lr=1e-2, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    y = np.copy(x0)
    t = 1.0
    for _ in range(max_iter):
        g = grad_f(y)
        x_new = prox(y - lr * g, lr)
        t_new = (1 + np.sqrt(1 + 4 * t ** 2)) / 2
        y = x_new + ((t - 1) / t_new) * (x_new - x)
        x = x_new
        t = t_new
        if np.linalg.norm(grad_f(x)) < tol:
            break
    return x


def soft_threshold(x, threshold):
    return np.sign(x) * np.maximum(np.abs(x) - threshold, 0.0)


def admm(f, grad_f, prox, x0, z0, u0, rho=1.0, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    z = np.copy(z0)
    u = np.copy(u0)
    for _ in range(max_iter):
        x = prox(x - (grad_f(x) + rho * (x - z + u)), 1.0 / rho)
        z_old = z
        z = prox(z + u, 1.0 / rho)
        u = u + x - z
        if np.linalg.norm(x - z) < tol and np.linalg.norm(z_old - z) < tol:
            break
    return x
