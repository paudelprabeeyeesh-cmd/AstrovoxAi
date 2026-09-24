import numpy as np


class SwiGLUActivation:
    def __init__(self, d_model, d_ff=None):
        if d_ff is None:
            d_ff = d_model * 4
        self.d_ff = d_ff
        self.W1 = np.random.randn(d_model, d_ff) * 0.02
        self.W2 = np.random.randn(d_ff, d_model) * 0.02
        self.W3 = np.random.randn(d_model, d_ff) * 0.02

    def swish(self, x):
        return x * (1.0 / (1.0 + np.exp(-x)))

    def forward(self, x):
        x1 = x @ self.W1
        x2 = x @ self.W3
        return (self.swish(x1) * x2) @ self.W2
