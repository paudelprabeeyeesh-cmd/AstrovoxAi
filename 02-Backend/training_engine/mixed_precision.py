import numpy as np


class MixedPrecisionTrainer:
    def __init__(self, params, lr=1e-3, loss_scale=65536.0, grad_clip=1.0, accumulation_steps=1):
        self.params = [np.copy(p).astype(np.float16) for p in params]
        self.master_params = [np.copy(p).astype(np.float32) for p in params]
        self.loss_scale = float(loss_scale)
        self.grad_clip = float(grad_clip)
        self.lr = float(lr)
        self.accumulation_steps = int(accumulation_steps)
        self.step = 0
        self._accum_grads = None

    def forward(self, x):
        return x @ self.params[0]

    def backward(self, logits, y, x):
        diff = logits - y
        grad = (2.0 / len(y)) * (x.T @ diff)
        return [grad]

    def _compute_grads(self, x, y, model_fn, loss_fn):
        logits = model_fn(x, self.params)
        loss = loss_fn(logits, y)
        grads = self.backward(logits, y, x)
        return grads, float(loss)

    def train_step(self, x, y, model_fn, loss_fn):
        grads, loss = self._compute_grads(x, y, model_fn, loss_fn)

        total_norm = float(np.sqrt(sum(np.sum(g ** 2) for g in grads)))
        if total_norm > self.grad_clip:
            grads = [g * (self.grad_clip / total_norm) for g in grads]

        if self._accum_grads is None:
            self._accum_grads = [np.zeros_like(g) for g in grads]

        for i, g in enumerate(grads):
            self._accum_grads[i] += g / self.accumulation_steps

        self.step += 1

        if self.step % self.accumulation_steps == 0:
            for i, (mp, ag) in enumerate(zip(self.master_params, self._accum_grads)):
                self.master_params[i] = mp - self.lr * ag
                self.params[i] = self.master_params[i].astype(np.float16)
            self._accum_grads = None

        return loss
