import numpy as np


def compute_hypergradient(loss_fn, params, optimizer, inner_steps=5, inner_lr=1e-2, epsilon=1e-4):
    base_loss = loss_fn(params)
    hypergrads = []
    for p in params:
        perturbation = np.zeros_like(p)
        flat_p = p.flatten()
        flat_grad = np.zeros_like(flat_p)
        for idx in range(len(flat_p)):
            perturbation_flat = np.zeros_like(flat_p)
            perturbation_flat[idx] = epsilon
            perturbation = perturbation_flat.reshape(p.shape)
            p_plus = p + perturbation
            p_minus = p - perturbation

            adapted_plus = _finite_diff_adapt(list(params), p_plus, optimizer, inner_steps, inner_lr)
            adapted_minus = _finite_diff_adapt(list(params), p_minus, optimizer, inner_steps, inner_lr)

            loss_plus = loss_fn(adapted_plus)
            loss_minus = loss_fn(adapted_minus)
            flat_grad[idx] = (loss_plus - loss_minus) / (2 * epsilon)
        hypergrads.append(flat_grad.reshape(p.shape))
    return hypergrads


def _finite_diff_adapt(params_list, perturbed_param, optimizer, inner_steps, inner_lr):
    adapted = [np.copy(p) for p in params_list]
    target_idx = next(i for i, p in enumerate(params_list) if p.shape == perturbed_param.shape and np.allclose(p, params_list[i]))
    adapted[target_idx] = perturbed_param
    for _ in range(inner_steps):
        g = _get_grads(adapted, optimizer)
        for i in range(len(adapted)):
            adapted[i] = adapted[i] - inner_lr * g[i]
    return adapted


def _get_grads(params, optimizer):
    return [np.random.randn(*p.shape) * 0.1 for p in params]


def hypergradient_descent(params, loss_fn, optimizer, meta_lr=1e-3, inner_steps=5, inner_lr=1e-2, epsilon=1e-4):
    hg = compute_hypergradient(loss_fn, params, optimizer, inner_steps, inner_lr, epsilon)
    updated = [p - meta_lr * g for p, g in zip(params, hg)]
    return updated, hg


class HypergradientOptimizer:
    def __init__(self, params, meta_lr=1e-3, inner_steps=5, inner_lr=1e-2, epsilon=1e-4):
        self.params = [np.copy(p) for p in params]
        self.meta_lr = float(meta_lr)
        self.inner_steps = int(inner_steps)
        self.inner_lr = float(inner_lr)
        self.epsilon = float(epsilon)
        self.history = []

    def step(self, loss_fn, optimizer):
        updated, hg = hypergradient_descent(
            self.params, loss_fn, optimizer, self.meta_lr, self.inner_steps, self.inner_lr, self.epsilon
        )
        self.params = updated
        self.history.append({"hypergrads": [np.copy(g) for g in hg], "loss": float(loss_fn(self.params))})
        return list(self.params)

    def get_params(self):
        return list(self.params)

    def get_history(self):
        return list(self.history)
