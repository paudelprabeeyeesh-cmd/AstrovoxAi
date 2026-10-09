
import numpy as np
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class MedusaHead:
    head_id: int
    input_dim: int
    output_dim: int
    weight: Optional[np.ndarray] = None
    bias: Optional[np.ndarray] = None

    def __post_init__(self):
        rng = np.random.default_rng(self.head_id + 1)
        self.weight = rng.standard_normal((self.output_dim, self.input_dim)).astype(np.float32) * 0.02
        self.bias = np.zeros(self.output_dim, dtype=np.float32)

    def forward(self, hidden: np.ndarray) -> np.ndarray:
        return hidden @ self.weight.T + self.bias


@dataclass
class MedusaConfig:
    num_heads: int = 4
    head_input_dim: int = 128
    head_output_dim: int = 1000
    tree_mask: Optional[np.ndarray] = None

    def __post_init__(self):
        if self.tree_mask is None:
            rng = np.random.default_rng(7)
            self.tree_mask = rng.integers(0, 2, size=(self.num_heads, self.num_heads)).astype(np.float32)


class MedusaHeads:
    def __init__(self, config: Optional[MedusaConfig] = None):
        if config is None:
            config = MedusaConfig()
        self.config = config
        self.heads = [
            MedusaHead(head_id=i, input_dim=config.head_input_dim,
                       output_dim=config.head_output_dim)
            for i in range(config.num_heads)
        ]

    def forward(self, hidden: np.ndarray) -> List[np.ndarray]:
        return [head.forward(hidden) for head in self.heads]

    def verify(self, draft_tokens: List[List[int]], target_logits: np.ndarray) -> List[bool]:
        verified = []
        target_probs = softmax(target_logits)
        if target_probs.ndim > 1:
            target_probs = target_probs[0]
        for head_idx, tokens in enumerate(draft_tokens):
            head_verified = True
            for token in tokens:
                if token < 0 or token >= len(target_probs):
                    head_verified = False
                    break
                draft_prob = float(target_probs[token])
                if draft_prob < 0.01:
                    head_verified = False
                    break
            verified.append(head_verified)
        return verified

    def generate_tree(self, hidden: np.ndarray, depth: int = 3) -> List[List[int]]:
        if depth <= 0:
            return []
        head_logits = self.forward(hidden)
        tree = []
        for head_idx, logits in enumerate(head_logits[:depth]):
            probs = softmax(logits)
            if probs.ndim > 1:
                top_token = int(np.argmax(probs[0]))
            else:
                top_token = int(np.argmax(probs))
            tree.append([top_token])
        return tree


def medusa_sampling(logits_list: List[np.ndarray], temperature: float = 1.0) -> List[List[int]]:
    sampled = []
    for logits in logits_list:
        probs = softmax(logits / max(temperature, 1e-9))
        if probs.ndim > 1:
            tokens = [int(np.argmax(probs[0]))]
        else:
            tokens = [int(np.argmax(probs))]
        sampled.append(tokens)
    return sampled


def softmax(x: np.ndarray) -> np.ndarray:
    x_max = np.max(x, axis=-1, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=-1, keepdims=True)
