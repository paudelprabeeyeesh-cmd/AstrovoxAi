import numpy as np


def spsa(f, x0, a=0.1, c=0.1, A=100, alpha=0.602, gamma=0.101, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    n = len(x)
    for k in range(1, max_iter + 1):
        ak = a / ((k + A) ** alpha)
        ck = c / (k ** gamma)
        delta = 2 * np.random.randint(0, 2, size=n) - 1
        x_plus = x + ck * delta
        x_minus = x - ck * delta
        y_plus = f(x_plus)
        y_minus = f(x_minus)
        g_hat = (y_plus - y_minus) / (2 * ck * delta)
        x_new = x - ak * g_hat
        if np.linalg.norm(x_new - x) < tol:
            break
        x = x_new
    return x


def stochastic_approximation(f, x0, lr=1e-2, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    for _ in range(max_iter):
        h = 1e-5
        g = np.zeros_like(x)
        for i in range(len(x)):
            e = np.zeros_like(x)
            e[i] = h
            g[i] = (f(x + e) - f(x - e)) / (2 * h)
        x_new = x - lr * g
        if np.linalg.norm(x_new - x) < tol:
            break
        x = x_new
    return x


def KieferWolfowitz(f, x0, h=1e-3, lr=1e-2, max_iter=100, tol=1e-6):
    x = np.copy(x0)
    n = len(x)
    for _ in range(max_iter):
        g = np.zeros(n)
        for i in range(n):
            e = np.zeros(n)
            e[i] = h
            g[i] = (f(x + e) - f(x - e)) / (2 * h)
        x_new = x - lr * g
        if np.linalg.norm(x_new - x) < tol:
            break
        x = x_new
    return x
