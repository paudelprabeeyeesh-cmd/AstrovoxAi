import numpy as np


class RBFSurrogate:
    def __init__(self, length_scale=1.0, noise=1e-6):
        self.length_scale = length_scale
        self.noise = noise
        self.x_train = None
        self.y_train = None
        self.K_inv = None

    def _kernel(self, x, y):
        return np.exp(-0.5 * np.sum((x - y) ** 2) / (self.length_scale ** 2))

    def fit(self, x_train, y_train):
        self.x_train = np.copy(x_train)
        self.y_train = np.copy(y_train)
        K = np.zeros((len(x_train), len(x_train)))
        for i in range(len(x_train)):
            for j in range(len(x_train)):
                K[i, j] = self._kernel(x_train[i], x_train[j])
        K = K + self.noise * np.eye(len(x_train))
        self.K_inv = np.linalg.inv(K + 1e-8 * np.eye(len(x_train)))

    def predict(self, x_test):
        k_star = np.array([self._kernel(xi, x_test) for xi in self.x_train])
        mean = k_star @ self.K_inv @ self.y_train
        var = self._kernel(x_test, x_test) - k_star @ self.K_inv @ k_star
        return mean, var


class PolynomialSurrogate:
    def __init__(self, degree=2):
        self.degree = degree
        self.coeffs = None

    def _build_design_matrix(self, X):
        n, d = X.shape
        exponents = []

        def generate(total, dims):
            if dims == 1:
                for e in range(total + 1):
                    exponents.append((e,))
            else:
                for e in range(total + 1):
                    for rest in generate(total - e, dims - 1):
                        exponents.append((e,) + rest)

        for p in range(self.degree + 1):
            generate(p, d)

        A = np.ones((n, 1))
        for exp in exponents:
            col = np.ones(n)
            for dim, order in enumerate(exp):
                col *= X[:, dim] ** order
            A = np.hstack((A, col.reshape(-1, 1)))
        return A

    def fit(self, x_train, y_train):
        A = self._build_design_matrix(np.copy(x_train))
        self.coeffs = np.linalg.lstsq(A, y_train, rcond=None)[0]

    def predict(self, x_test):
        A = self._build_design_matrix(np.copy(x_test))
        return A @ self.coeffs
