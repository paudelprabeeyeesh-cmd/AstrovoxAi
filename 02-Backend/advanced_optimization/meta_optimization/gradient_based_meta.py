import numpy as np


def maml_inner_loop(params, loss_fn, grads_fn, inner_steps=5, inner_lr=1e-2):
    adapted = [np.copy(p) for p in params]
    for _ in range(inner_steps):
        g = grads_fn(adapted)
        for i in range(len(adapted)):
            adapted[i] = adapted[i] - inner_lr * g[i]
    return adapted


def maml_outer_loss(adapted_params, val_loss_fn):
    return float(val_loss_fn(adapted_params))


def reptile_update(params, new_params, meta_lr=1e-3):
    updated = []
    for p, np_ in zip(params, new_params):
        updated.append(p + meta_lr * (np_ - p))
    return updated


class MAMLTrainer:
    def __init__(self, params, loss_fn, grads_fn, val_loss_fn, inner_steps=5, inner_lr=1e-2, meta_lr=1e-3):
        self.params = [np.copy(p) for p in params]
        self.loss_fn = loss_fn
        self.grads_fn = grads_fn
        self.val_loss_fn = val_loss_fn
        self.inner_steps = inner_steps
        self.inner_lr = float(inner_lr)
        self.meta_lr = float(meta_lr)

    def adapt(self, task_params=None):
        base = task_params if task_params is not None else self.params
        return maml_inner_loop(base, self.loss_fn, self.grads_fn, self.inner_steps, self.inner_lr)

    def meta_step(self, task_grads):
        for i in range(len(self.params)):
            self.params[i] = self.params[i] - self.meta_lr * task_grads[i]
        return list(self.params)

    def evaluate(self, adapted_params):
        return maml_outer_loss(adapted_params, self.val_loss_fn)


class ReptileTrainer:
    def __init__(self, params, meta_lr=1e-3):
        self.params = [np.copy(p) for p in params]
        self.meta_lr = float(meta_lr)

    def step(self, new_params):
        self.params = reptile_update(self.params, new_params, self.meta_lr)
        return list(self.params)

    def get_params(self):
        return list(self.params)
