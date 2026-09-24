import numpy as np


class LearnedOptimizer:
    def __init__(self, num_params, hidden_size=32):
        self.num_params = num_params
        self.hidden_size = hidden_size
        self.w1 = np.random.randn(num_params, hidden_size) * 0.01
        self.w2 = np.random.randn(hidden_size, num_params) * 0.01
        self.b1 = np.zeros(hidden_size)
        self.b2 = np.zeros(num_params)
        self.m = [np.zeros_like(self.w1), np.zeros_like(self.w2), np.zeros_like(self.b1), np.zeros_like(self.b2)]
        self.v = [np.zeros_like(self.w1), np.zeros_like(self.w2), np.zeros_like(self.b1), np.zeros_like(self.b2)]
        self.t = 0

    def _update(self, params, grads, lr=1e-3):
        self.t += 1
        x = np.concatenate([p.flatten() for p in params])
        g = np.concatenate([gr.flatten() for gr in grads])
        h1 = np.maximum(0, x @ self.w1 + self.b1)
        update = h1 @ self.w2 + self.b2
        for i, (p, gr) in enumerate(zip(params, grads)):
            p_flat_idx = sum(np.prod(params[j].shape) for j in range(i))
            p_flat_size = np.prod(p.shape)
            p -= lr * update[p_flat_idx:p_flat_idx + p_flat_size].reshape(p.shape)
        return params

    def step(self, params, grads, lr=1e-3):
        return self._update(params, grads, lr)


class SimpleLSTMOptimizer:
    def __init__(self, num_params, hidden_size=32):
        self.num_params = num_params
        self.hidden_size = hidden_size
        self.wf = np.random.randn(hidden_size + num_params, hidden_size) * 0.01
        self.wi = np.random.randn(hidden_size + num_params, hidden_size) * 0.01
        self.wo = np.random.randn(hidden_size + num_params, hidden_size) * 0.01
        self.wg = np.random.randn(hidden_size + num_params, hidden_size) * 0.01
        self.wy = np.random.randn(hidden_size, num_params) * 0.01
        self.h = np.zeros(hidden_size)
        self.c = np.zeros(hidden_size)

    def step(self, params, grads):
        x = np.concatenate([p.flatten() for p in params])
        g = np.concatenate([gr.flatten() for gr in grads])
        combined = np.concatenate([x, self.h])
        f = 1 / (1 + np.exp(-(combined @ self.wf)))
        i = 1 / (1 + np.exp(-(combined @ self.wi)))
        o = 1 / (1 + np.exp(-(combined @ self.wo)))
        g_t = np.tanh(combined @ self.wg)
        self.c = f * self.c + i * g_t
        self.h = o * np.tanh(self.c)
        update = self.h @ self.wy
        for i, (p, gr) in enumerate(zip(params, grads)):
            p_flat_idx = sum(np.prod(params[j].shape) for j in range(i))
            p_flat_size = np.prod(p.shape)
            p -= update[p_flat_idx:p_flat_idx + p_flat_size].reshape(p.shape)
        return params
