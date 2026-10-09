import numpy as np


def co_kriging(x_low, y_low, x_high, y_high, x_test, length_scale=1.0, noise=1e-6):
    def rbf(x, y):
        return np.exp(-0.5 * np.sum((x - y) ** 2) / (length_scale ** 2))

    K_low = np.zeros((len(x_low), len(x_low)))
    for i in range(len(x_low)):
        for j in range(len(x_low)):
            K_low[i, j] = rbf(x_low[i], x_low[j])
    K_low += noise * np.eye(len(x_low))

    K_high = np.zeros((len(x_high), len(x_high)))
    for i in range(len(x_high)):
        for j in range(len(x_high)):
            K_high[i, j] = rbf(x_high[i], x_high[j])
    K_high += noise * np.eye(len(x_high))

    k_low_test = np.array([rbf(xi, x_test) for xi in x_low])
    k_high_test = np.array([rbf(xi, x_test) for xi in x_high])

    K_low_inv = np.linalg.inv(K_low + 1e-8 * np.eye(len(x_low)))
    K_high_inv = np.linalg.inv(K_high + 1e-8 * np.eye(len(x_high)))

    rho = np.sum(y_high * (K_high_inv @ k_high_test)) / (np.sum(K_high_inv @ k_high_test) + 1e-9)
    mean_low = k_low_test @ K_low_inv @ y_low
    mean = rho * mean_low
    return mean


def multi_fidelity_optimize(f_low, f_high, bounds, n_low=30, n_high=10, max_iter=10):
    dim = len(bounds)
    x_low = np.array([np.random.uniform(b[0], b[1]) for b in bounds for _ in range(n_low)])
    y_low = np.array([f_low(x) for x in x_low])

    x_high = np.array([np.random.uniform(b[0], b[1]) for b in bounds for _ in range(n_high)])
    y_high = np.array([f_high(x) for x in x_high])

    candidates = np.array([np.random.uniform(b[0], b[1]) for b in bounds for _ in range(50)])
    best_ei = -1
    best_x = None
    best_f = np.min(y_high)
    for x in candidates:
        pred = co_kriging(x_low, y_low, x_high, y_high, x)
        ei = max(pred - best_f, 0)
        if ei > best_ei:
            best_ei = ei
            best_x = x
    return best_x if best_x is not None else candidates[0]
