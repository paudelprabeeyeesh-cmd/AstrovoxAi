import numpy as np


class RMSPropWrapper:
    def __init__(self, params, lr=1e-2, alpha=0.99, eps=1e-8):
        self.params = [np.copy(p) for p in params]
        self.lr = float(lr)
        self.alpha = float(alpha)
        self.eps = float(eps)
        self.cache = [np.zeros_like(p) for p in self.params]

    def step(self, grads):
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.cache[i] = self.alpha * self.cache[i] + (1 - self.alpha) * (g ** 2)
            self.params[i] = p - self.lr * g / (np.sqrt(self.cache[i]) + self.eps)
        return list(self.params)
