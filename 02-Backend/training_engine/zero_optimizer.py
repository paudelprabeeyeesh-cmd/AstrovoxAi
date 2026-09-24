import numpy as np


class ZeROOptimizer:
    def __init__(self, params, lr=1e-3, stage=1, world_size=1):
        self.params = [np.copy(p) for p in params]
        self.lr = float(lr)
        self.stage = int(stage)
        self.world_size = int(world_size)
        self.optim_states = [{"m": np.zeros_like(p), "v": np.zeros_like(p)} for p in self.params]

    def partition(self, state, rank):
        return np.array_split(state, self.world_size)[rank]

    def step(self, grads, rank=0):
        new_params = []
        for i, (p, g) in enumerate(zip(self.params, grads)):
            if self.stage >= 3:
                p = self.partition(p, rank)
                g = self.partition(g, rank)
                m = self.partition(self.optim_states[i]["m"], rank)
                v = self.partition(self.optim_states[i]["v"], rank)
                m[:] = 0.9 * m + 0.1 * g
                v[:] = 0.999 * v + 0.001 * (g ** 2)
                p_new = p - self.lr * (m / (np.sqrt(v) + 1e-8) + 0.01 * p)
            else:
                m = self.optim_states[i]["m"]
                v = self.optim_states[i]["v"]
                m[:] = 0.9 * m + 0.1 * g
                v[:] = 0.999 * v + 0.001 * (g ** 2)
                p_new = p - self.lr * (m / (np.sqrt(v) + 1e-8) + 0.01 * p)
            new_params.append(p_new)
        self.params = new_params
        return list(self.params)
