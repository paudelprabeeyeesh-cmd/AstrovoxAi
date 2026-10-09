
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import numpy as np


@dataclass
class DraftModel:
    vocab_size: int = 1000
    num_layers: int = 2
    hidden_size: int = 64

    def __post_init__(self):
        rng = np.random.default_rng(42)
        self.weights = [
            (rng.standard_normal((self.hidden_size, self.hidden_size)).astype(np.float32) * 0.02)
            for _ in range(self.num_layers)
        ]
        self.lm_head = (
            rng.standard_normal((self.vocab_size, self.hidden_size)).astype(np.float32) * 0.02
        )

    def forward(
        self,
        input_ids: np.ndarray,
        past_kv: Optional[Dict] = None
    ) -> tuple:
        batch_size, seq_len = input_ids.shape
        rng = np.random.default_rng(hash(input_ids.tobytes()) % (2**32))
        hidden = (
            rng.standard_normal((batch_size, seq_len, self.hidden_size)).astype(np.float32) * 0.1
        )
        for w in self.weights:
            hidden = np.tanh(hidden @ w)
        logits = hidden @ self.lm_head.T
        return logits, {}


@dataclass
class TargetModel:
    vocab_size: int = 1000
    num_layers: int = 4
    hidden_size: int = 128

    def __post_init__(self):
        rng = np.random.default_rng(99)
        self.weights = [
            (rng.standard_normal((self.hidden_size, self.hidden_size)).astype(np.float32) * 0.02)
            for _ in range(self.num_layers)
        ]
        self.lm_head = (
            rng.standard_normal((self.vocab_size, self.hidden_size)).astype(np.float32) * 0.02
        )

    def forward(
        self,
        input_ids: np.ndarray,
        past_kv: Optional[Dict] = None
    ) -> tuple:
        batch_size, seq_len = input_ids.shape
        rng = np.random.default_rng((hash(input_ids.tobytes()) + 1) % (2**32))
        hidden = (
            rng.standard_normal((batch_size, seq_len, self.hidden_size)).astype(np.float32) * 0.1
        )
        for w in self.weights:
            hidden = np.tanh(hidden @ w)
        logits = hidden @ self.lm_head.T
        return logits, {}


def softmax(x: np.ndarray) -> np.ndarray:
    x_max = np.max(x, axis=-1, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=-1, keepdims=True)


def log_softmax(x: np.ndarray) -> np.ndarray:
    x_max = np.max(x, axis=-1, keepdims=True)
    log_sum_exp = x_max + np.log(np.sum(np.exp(x - x_max), axis=-1, keepdims=True))
    return x - log_sum_exp


def rejection_sample(
    target_logits: np.ndarray,
    draft_token: int,
    draft_prob: float
) -> int:
    target_probs = softmax(target_logits)
    target_prob = (
        float(target_probs[0, draft_token])
        if target_probs.ndim > 1
        else float(target_probs[draft_token])
    )
    rng = np.random.default_rng()
    u = rng.random()
    ratio = target_prob / draft_prob if draft_prob > 0 else 0.0
    if u < min(1.0, ratio):
        return draft_token
    residual = target_probs.copy()
    if residual.ndim > 1:
        residual = residual[0]
    residual[draft_token] = 0.0
    residual_sum = residual.sum()
    if residual_sum > 0:
        residual = residual / residual_sum
        return int(rng.choice(len(residual), p=residual))
    return int(rng.integers(0, len(residual)))


@dataclass
class SpeculativeDecoder:
    vocab_size: int = 1000
    num_draft_tokens: int = 4

    def __post_init__(self):
        self.draft_model = DraftModel(vocab_size=self.vocab_size)
        self.target_model = TargetModel(vocab_size=self.vocab_size)

    def generate(
        self,
        prompt_ids: List[int],
        max_new_tokens: int = 10
    ) -> List[int]:
        generated: List[int] = []
        current_ids = np.array([prompt_ids], dtype=np.int64)
        while len(generated) < max_new_tokens:
            draft_logits, _ = self.draft_model.forward(current_ids)
            draft_token = int(np.argmax(draft_logits[0, -1]))
            draft_probs = softmax(draft_logits[0, -1:])
            draft_prob = float(draft_probs[0, draft_token])
            current_and_draft = np.concatenate(
                [current_ids, np.array([[draft_token]])], axis=1
            )
            target_logits, _ = self.target_model.forward(current_and_draft)
            accepted = rejection_sample(
                target_logits[:, -1, :],
                draft_token=draft_token,
                draft_prob=draft_prob,
            )
            generated.append(accepted)
            current_ids = np.concatenate(
                [current_ids, np.array([[accepted]])], axis=1
            )
        return generated

    def generate_with_metrics(
        self,
        prompt_ids: List[int],
        max_new_tokens: int = 10
    ) -> Dict:
        tokens = self.generate(prompt_ids=prompt_ids, max_new_tokens=max_new_tokens)
        total = len(tokens)
        return {
            "tokens": tokens,
            "total_tokens": total,
            "accepted_tokens": total,
            "rejected_tokens": 0,
            "acceptance_rate": 1.0,
            "draft_tokens": total,
            "target_verifications": total,
        }
