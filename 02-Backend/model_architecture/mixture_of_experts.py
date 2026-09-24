import numpy as np
from .rmsnorm import RMSNorm


class Expert:
    def __init__(self, d_model, d_ff):
        self.W1 = np.random.randn(d_model, d_ff) * 0.02
        self.W2 = np.random.randn(d_ff, d_model) * 0.02
        self.b1 = np.zeros(d_ff)
        self.b2 = np.zeros(d_model)
        self.norm = RMSNorm(d_model)

    def forward(self, x):
        h = np.maximum(0, x @ self.W1 + self.b1)
        return self.norm.forward(h @ self.W2 + self.b2)


class Router:
    def __init__(self, d_model, num_experts):
        self.W = np.random.randn(d_model, num_experts) * 0.02

    def forward(self, x):
        logits = x @ self.W
        probs = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = probs / np.sum(probs, axis=-1, keepdims=True)
        return probs


class MoELayer:
    def __init__(self, d_model, num_experts=8, d_ff=None, top_k=2):
        if not (0 < top_k <= num_experts):
            raise AssertionError("top_k must be between 1 and num_experts")
        self.num_experts = num_experts
        self.top_k = top_k
        self.d_ff = d_ff if d_ff is not None else d_model * 4
        self.experts = [Expert(d_model, self.d_ff) for _ in range(num_experts)]
        self.router = Router(d_model, num_experts)

    def forward(self, x):
        B, T, C = x.shape
        flat = x.reshape(-1, C)
        probs = self.router.forward(flat)
        topk_probs, topk_idx = np.sort(probs, axis=-1)[:, -self.top_k:], np.argsort(probs, axis=-1)[:, -self.top_k:]
        topk_probs = topk_probs / np.sum(topk_probs, axis=-1, keepdims=True)

        out = np.zeros_like(flat)
        for i in range(self.top_k):
            for e in range(self.num_experts):
                mask = topk_idx[:, i] == e
                if np.any(mask):
                    out[mask] += topk_probs[mask, i:i+1] * self.experts[e].forward(flat[mask])
        return out.reshape(B, T, C)

    def load_balancing_loss(self, x):
        flat = x.reshape(-1, x.shape[-1])
        probs = self.router.forward(flat)
        mean_probs = np.mean(probs, axis=0)
        uniform = np.ones(self.num_experts) / self.num_experts
        return np.sum(mean_probs * np.log(mean_probs / uniform))
