
import numpy as np
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class EAGLEDraftModel:
    vocab_size: int = 1000
    hidden_size: int = 128
    feature_dim: int = 64

    def __post_init__(self):
        rng = np.random.default_rng(77)
        self.feature_proj = rng.standard_normal((self.feature_dim, self.hidden_size)).astype(np.float32) * 0.02
        self.draft_head = rng.standard_normal((self.vocab_size, self.feature_dim)).astype(np.float32) * 0.02
        self.feature_bias = np.zeros(self.feature_dim, dtype=np.float32)

    def extract_features(self, hidden: np.ndarray) -> np.ndarray:
        return np.maximum(0, hidden @ self.feature_proj.T + self.feature_bias)

    def draft_forward(self, hidden: np.ndarray) -> np.ndarray:
        features = self.extract_features(hidden)
        return features @ self.draft_head.T

    def generate_draft_tokens(self, hidden: np.ndarray, num_tokens: int = 3) -> List[int]:
        logits = self.draft_forward(hidden)
        tokens = []
        current_hidden = hidden
        rng = np.random.default_rng(77)
        for _ in range(num_tokens):
            probs = softmax(logits)
            probs_1d = probs.reshape(-1)
            probs_1d = np.clip(probs_1d, 0, None)
            s = probs_1d.sum()
            if s > 0:
                probs_1d = probs_1d / s
            else:
                probs_1d = np.ones_like(probs_1d) / len(probs_1d)
            token = int(rng.choice(len(probs_1d), p=probs_1d))
            tokens.append(token)
            rng2 = np.random.default_rng(token + 1)
            current_hidden = rng2.standard_normal(current_hidden.shape).astype(np.float32) * 0.1
            logits = self.draft_forward(current_hidden)
        return tokens


class EAGLESpeculativeDecoder:
    def __init__(self, vocab_size: int = 1000, num_draft_tokens: int = 4):
        self.vocab_size = vocab_size
        self.num_draft_tokens = num_draft_tokens
        self.draft_model = EAGLEDraftModel(vocab_size=vocab_size)
        self.target_model = TargetModel(vocab_size=vocab_size)
        self.acceptance_buffer: List[int] = []
        self.rejection_buffer: List[Tuple[int, float]] = []

    def draft_step(self, hidden: np.ndarray) -> Tuple[List[int], np.ndarray]:
        tokens = self.draft_model.generate_draft_tokens(hidden, self.num_draft_tokens)
        features = self.draft_model.extract_features(hidden)
        return tokens, features

    def verify_step(self, hidden: np.ndarray, draft_tokens: List[int]) -> Tuple[List[int], int, int]:
        target_logits, _ = self.target_model.forward(hidden)
        target_probs = softmax(target_logits)
        target_probs = np.asarray(target_probs)
        while target_probs.ndim > 1:
            target_probs = target_probs[0]
        accepted = []
        rejected = 0
        for token in draft_tokens:
            if token < 0 or token >= len(target_probs):
                rejected += 1
                continue
            t_prob = float(target_probs[token])
            rng = np.random.default_rng()
            u = rng.random()
            if u < min(1.0, t_prob / 0.1) if 0.1 > 0 else 0.0:
                accepted.append(token)
            else:
                rejected += 1
                residual = target_probs.copy()
                residual[token] = 0.0
                s = residual.sum()
                if s > 0:
                    residual = residual / s
                    accepted.append(int(rng.choice(len(residual), p=residual)))
                break
        return accepted, len(accepted), rejected

    def speculative_generate(self, prompt_ids: List[int], max_new_tokens: int = 10) -> Tuple[List[int], Dict]:
        generated = []
        metrics = {"draft_tokens": 0, "accepted": 0, "rejected": 0, "steps": 0}
        hidden = np.zeros((1, len(prompt_ids), 128), dtype=np.float32)
        rng = np.random.default_rng(7)
        hidden = rng.standard_normal(hidden.shape).astype(np.float32) * 0.1
        current_ids = prompt_ids
        while len(generated) < max_new_tokens:
            draft_tokens, features = self.draft_step(hidden[:, -1, :])
            metrics["draft_tokens"] += len(draft_tokens)
            target_hidden = np.concatenate([hidden, hidden[:, -1:, :].repeat(len(draft_tokens), axis=1)], axis=1)
            accepted, n_acc, n_rej = self.verify_step(target_hidden[:, -1, :], draft_tokens)
            metrics["accepted"] += n_acc
            metrics["rejected"] += n_rej
            metrics["steps"] += 1
            generated.extend(accepted[:max_new_tokens - len(generated)])
            current_ids.extend(accepted)
            if len(generated) >= max_new_tokens:
                break
            rng2 = np.random.default_rng(sum(current_ids) + 1)
            hidden = rng2.standard_normal((1, len(current_ids), 128)).astype(np.float32) * 0.1
        return generated, metrics


@dataclass
class TargetModel:
    vocab_size: int = 1000
    num_layers: int = 4
    hidden_size: int = 128

    def __post_init__(self):
        rng = np.random.default_rng(99)
        self.weights = [rng.standard_normal((self.hidden_size, self.hidden_size)).astype(np.float32) * 0.02
                        for _ in range(self.num_layers)]
        self.lm_head = rng.standard_normal((self.vocab_size, self.hidden_size)).astype(np.float32) * 0.02

    def forward(self, input_ids: np.ndarray, past_kv: Optional[Dict] = None) -> tuple[np.ndarray, Dict]:
        batch_size, seq_len = input_ids.shape if input_ids.ndim == 2 else (1, 1)
        if input_ids.ndim == 3:
            batch_size, seq_len, hidden_size = input_ids.shape
            hidden = input_ids
        else:
            rng = np.random.default_rng((hash(input_ids.tobytes()) + 1) % (2**32))
            hidden = rng.standard_normal((batch_size, seq_len, self.hidden_size)).astype(np.float32) * 0.1
        for w in self.weights:
            hidden = np.tanh(hidden @ w)
        logits = hidden @ self.lm_head.T
        return logits, {}


def softmax(x: np.ndarray) -> np.ndarray:
    x_max = np.max(x, axis=-1, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=-1, keepdims=True)
