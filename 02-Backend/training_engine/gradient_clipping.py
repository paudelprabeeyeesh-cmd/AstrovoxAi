import numpy as np


def clip_grad_norm(params_grads, max_norm):
    total_norm = float(np.sqrt(sum(np.sum(g ** 2) for _, g in params_grads)))
    if total_norm > max_norm:
        clip_coef = max_norm / (total_norm + 1e-6)
        return [(p, g * clip_coef) for p, g in params_grads], total_norm
    return list(params_grads), total_norm
