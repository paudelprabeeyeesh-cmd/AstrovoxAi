import numpy as np


class AdagradWrapper:
    def __init__(self, params, lr=1e-2, eps=1e-8):
        self.params = [np.copy(p) for p in params]
        self.lr = float(lr)
        self.eps = float(eps)
        self.sum = [np.zeros_like(p) for p in self.params]

    def step(self, grads):
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.sum[i] = self.sum[i] + (g ** 2)
            self.params[i] = p - self.lr * g / (np.sqrt(self.sum[i]) + self.eps)
        return list(self.params)
