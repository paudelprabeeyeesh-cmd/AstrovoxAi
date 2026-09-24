import numpy as np


def rbf_kernel(x, y, length_scale=1.0):
    return np.exp(-0.5 * np.sum((x - y) ** 2) / (length_scale ** 2))


def gaussian_process(x_train, y_train, x_test, length_scale=1.0, noise=1e-6):
    K = np.zeros((len(x_train), len(x_train)))
    for i in range(len(x_train)):
        for j in range(len(x_train)):
            K[i, j] = rbf_kernel(x_train[i], x_train[j], length_scale) + (noise if i == j else 0)
    K_inv = np.linalg.inv(K + 1e-8 * np.eye(len(x_train)))
    k_star = np.array([rbf_kernel(xi, x_test, length_scale) for xi in x_train])
    mean = k_star @ K_inv @ y_train
    var = rbf_kernel(x_test, x_test, length_scale) - k_star @ K_inv @ k_star
    return mean, var


def expected_improvement(mean, var, best_f):
    std = np.sqrt(max(var, 1e-9))
    with np.errstate(divide='ignore', invalid='ignore'):
        z = (mean - best_f) / std
        ei = (mean - best_f) * 0.5 * (1 + np.sign(mean - best_f) * np.tanh(z)) + std * (1 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * z ** 2)
        ei = np.where(var > 1e-9, ei, 0.0)
    return ei


def bayesian_optimize(f, bounds, n_init=5, n_iter=20, length_scale=1.0):
    dim = len(bounds)
    xs = np.array([np.random.uniform(b[0], b[1], dim) for b in bounds for _ in range(n_init)])
    ys = np.array([f(x) for x in xs])
    best_f = np.min(ys)
    for _ in range(n_iter):
        candidates = np.array([np.random.uniform(b[0], b[1], dim) for b in bounds for _ in range(50)])
        best_ei = -1
        best_x = None
        for x in candidates:
            mean, var = gaussian_process(xs, ys, x, length_scale)
            ei = expected_improvement(mean, var, best_f)
            if ei > best_ei:
                best_ei = ei
                best_x = x
        if best_x is None:
            best_x = candidates[0]
        y = f(best_x)
        xs = np.vstack([xs, best_x])
        ys = np.append(ys, y)
        if y < best_f:
            best_f = y
    best_idx = np.argmin(ys)
    return xs[best_idx]
