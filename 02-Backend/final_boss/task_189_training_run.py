import numpy as np


class TrainingRun:
    def __init__(self, tokens=15e12, batch_size=4096, lr=3e-4):
        self.total_tokens = tokens
        self.batch_size = batch_size
        self.lr = lr
        self.step = 0
        self.tokens_seen = 0.0
        self.losses = []
        self.checkpoints = []

    def forward(self, x):
        w = np.random.randn(x.shape[1], 512)
        return x @ w

    def backward(self, x, y, pred):
        loss = np.mean((pred - y) ** 2)
        return loss

    def optimizer_step(self):
        self.lr *= 0.999

    def checkpoint(self):
        ckpt = {"step": self.step, "tokens": self.tokens_seen, "loss": np.mean(self.losses[-100:]) if self.losses else None}
        self.checkpoints.append(ckpt)
        return ckpt

    def train_step(self, x, y):
        pred = self.forward(x)
        loss = self.backward(x, y, pred)
        self.optimizer_step()
        self.losses.append(loss)
        self.tokens_seen += self.batch_size
        self.step += 1
        return loss

    def handle_failure(self):
        return self.checkpoints[-1] if self.checkpoints else None
