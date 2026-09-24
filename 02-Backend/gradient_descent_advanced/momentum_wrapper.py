import numpy as np


class MomentumWrapper:
    def __init__(self, params, lr=1e-2, momentum=0.9):
        self.params = [np.copy(p) for p in params]
        self.lr = float(lr)
        self.momentum = float(momentum)
        self.velocity = [np.zeros_like(p) for p in self.params]

    def step(self, grads):
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.velocity[i] = self.momentum * self.velocity[i] + g
            self.params[i] = p - self.lr * self.velocity[i]
        return list(self.params)
