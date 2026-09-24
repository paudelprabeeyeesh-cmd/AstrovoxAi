import numpy as np


def cyclic_coordinate_descent(f, grad_f, x0, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    n = len(x)
    for _ in range(max_iter):
        for i in range(n):
            g = grad_f(x)
            step = g[i]
            x_new = np.copy(x)
            x_new[i] -= step
            if f(x_new) < f(x):
                x = x_new
        g = grad_f(x)
        if np.linalg.norm(g) < tol:
            break
    return x


def gauss_southwell(f, grad_f, x0, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    for _ in range(max_iter):
        g = grad_f(x)
        i = np.argmax(np.abs(g))
        step = g[i]
        x_new = np.copy(x)
        x_new[i] -= step
        if f(x_new) < f(x):
            x = x_new
        if np.linalg.norm(grad_f(x)) < tol:
            break
    return x


def block_coordinate_descent(f, grad_f, x0, blocks, max_iter=1000, tol=1e-6):
    x = np.copy(x0)
    for _ in range(max_iter):
        for block in blocks:
            g = grad_f(x)
            x_new = np.copy(x)
            x_new[block] = x[block] - g[block]
            if f(x_new) < f(x):
                x = x_new
        if np.linalg.norm(grad_f(x)) < tol:
            break
    return x
