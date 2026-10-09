import numpy as np


def newton_step_1d(f, grad, hess, x0, tol=1e-6, max_iter=100):
    x = float(x0)
    for _ in range(max_iter):
        g = grad(x)
        h = hess(x)
        if abs(h) < 1e-12:
            break
        step = g / h
        if abs(step) < tol:
            break
        x = x - step
    return x


def newton_step_multi(params, grad_fn, hess_fn, tol=1e-6, max_iter=100):
    x = np.copy(params)
    for _ in range(max_iter):
        g = grad_fn(x)
        h = hess_fn(x)
        try:
            h_inv = np.linalg.inv(h)
        except np.linalg.LinAlgError:
            h_inv = np.linalg.pinv(h)
        step = h_inv @ g
        if np.linalg.norm(step) < tol:
            break
        x = x - step
    return x


def damped_newton(params, grad_fn, hess_fn, alpha=1.0, beta=0.5, max_iter=100):
    x = np.copy(params)
    for _ in range(max_iter):
        g = grad_fn(x)
        h = hess_fn(x)
        try:
            h_inv = np.linalg.inv(h)
        except np.linalg.LinAlgError:
            h_inv = np.linalg.pinv(h)
        direction = h_inv @ g
        step = alpha * direction
        while grad_fn(x - step) @ step > 0.5 * step @ h @ step:
            alpha *= beta
            step = alpha * direction
        x = x - step
    return x


def bfgs_update(H, s, y):
    rho = 1.0 / (y @ s)
    identity_mat = np.eye(H.shape[0])
    H @ y
    H = (identity_mat - rho * np.outer(s, y)) @ H @ (identity_mat - rho * np.outer(y, s)) + rho * np.outer(s, s)
    return H


def bfgs(params, grad_fn, max_iter=100, tol=1e-6):
    x = np.copy(params)
    n = x.shape[0]
    H = np.eye(n)
    g = grad_fn(x)
    for _ in range(max_iter):
        p = -H @ g
        if np.linalg.norm(p) < tol:
            break
        x_new = x + p
        s = x_new - x
        y = grad_fn(x_new) - g
        if s @ y > 1e-10:
            H = bfgs_update(H, s, y)
        x = x_new
        g = grad_fn(x)
    return x
