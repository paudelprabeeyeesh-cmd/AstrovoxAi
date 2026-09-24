import numpy as np


def warm_start_from_params(source_params, target_shape_fn, scale=1.0):
    source_vec = np.concatenate([p.flatten() for p in source_params])
    target_shapes = target_shape_fn()
    total = sum(int(np.prod(s)) for s in target_shapes)
    if total <= len(source_vec):
        vec = source_vec[:total]
    else:
        vec = np.tile(source_vec, int(np.ceil(total / len(source_vec))))[:total]
    vec = vec * float(scale)
    result = []
    offset = 0
    for shape in target_shapes:
        size = int(np.prod(shape))
        result.append(vec[offset:offset + size].reshape(shape))
        offset += size
    return result


def warm_start_adam_state(params, beta1=0.9, beta2=0.999, eps=1e-8):
    m = [np.zeros_like(p) for p in params]
    v = [np.zeros_like(p) for p in params]
    t = 0
    return {"m": m, "v": v, "t": t, "beta1": float(beta1), "beta2": float(beta2), "eps": float(eps)}


def interpolate_initialization(base_params, fine_tuned_params, alpha=0.5):
    alpha = float(alpha)
    return [alpha * bp + (1 - alpha) * ftp for bp, ftp in zip(base_params, fine_tuned_params)]


class WarmStartStrategy:
    def __init__(self, params, strategy="copy", scale=1.0):
        self.original = [np.copy(p) for p in params]
        self.strategy = strategy
        self.scale = float(scale)

    def initialize(self, target_params):
        if self.strategy == "copy":
            return [np.copy(p) for p in self.original]
        if self.strategy == "source":
            return warm_start_from_params(self.original, lambda: [p.shape for p in target_params], self.scale)
        if self.strategy == "zeros":
            return [np.zeros_like(p) for p in target_params]
        if self.strategy == "random":
            return [np.random.randn(*p.shape).astype(p.dtype) * self.scale for p in target_params]
        raise ValueError(f"Unknown strategy: {self.strategy}")
