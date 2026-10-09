import numpy as np


class SGD:
    def __init__(self, params, lr=1e-2):
        self.params = [np.copy(p) for p in params]
        self.lr = float(lr)

    def step(self, grads):
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.params[i] = p - self.lr * g
        return list(self.params)


class MomentumSGD:
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


class NesterovSGD:
    def __init__(self, params, lr=1e-2, momentum=0.9):
        self.params = [np.copy(p) for p in params]
        self.lr = float(lr)
        self.momentum = float(momentum)
        self.velocity = [np.zeros_like(p) for p in self.params]

    def step(self, grads):
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.velocity[i] = self.momentum * self.velocity[i] + g
            self.params[i] = p - self.lr * (self.momentum * self.velocity[i] + g)
        return list(self.params)


class Adam:
    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8):
        self.params = [np.copy(p) for p in params]
        self.lr = float(lr)
        self.beta1, self.beta2 = betas
        self.eps = float(eps)
        self.t = 0
        self.m = [np.zeros_like(p) for p in self.params]
        self.v = [np.zeros_like(p) for p in self.params]

    def step(self, grads):
        self.t += 1
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.m[i] = self.beta1 * self.m[i] + (1 - self.beta1) * g
            self.v[i] = self.beta2 * self.v[i] + (1 - self.beta2) * (g ** 2)
            bias1 = 1 - self.beta1 ** self.t
            bias2 = 1 - self.beta2 ** self.t
            m_hat = self.m[i] / bias1
            v_hat = self.v[i] / bias2
            self.params[i] = p - self.lr * m_hat / (np.sqrt(v_hat) + self.eps)
        return list(self.params)
