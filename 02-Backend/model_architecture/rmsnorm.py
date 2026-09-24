import numpy as np


class RMSNorm:
    def __init__(self, d_model, eps=1e-6):
        self.gamma = np.ones(d_model)
        self.eps = eps

    def forward(self, x):
        norm = np.sqrt(np.mean(x ** 2, axis=-1, keepdims=True) + self.eps)
        return (x / norm) * self.gamma
