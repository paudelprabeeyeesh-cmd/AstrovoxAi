import numpy as np


def cyclic_coordinate_descent(f, grad_f, x0, lr=1e-2, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    n = len(x)
    for _ in range(max_iter):
        for i in range(n):
            g = grad_f(x)
            x[i] -= lr * g[i]
        if np.linalg.norm(grad_f(x)) < tol:
            break
    return x


def gauss_southwell(f, grad_f, x0, lr=1e-2, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    for _ in range(max_iter):
        g = grad_f(x)
        i = np.argmax(np.abs(g))
        x[i] -= lr * g[i]
        if np.linalg.norm(grad_f(x)) < tol:
            break
    return x


def block_coordinate_descent(f, grad_f, x0, blocks, lr=1e-2, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    for _ in range(max_iter):
        for block in blocks:
            g = grad_f(x)
            x[block] -= lr * g[block]
        if np.linalg.norm(grad_f(x)) < tol:
            break
    return x
