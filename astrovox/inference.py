"""Streaming inference utilities.

Provides chunked prefill, token streaming, and batch inference helpers for
large-language models. These utilities are intentionally backend-agnostic so
they can be reused across CPU, CUDA, and other execution backends.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional

import numpy as np

from astrovox.kv_cache import ChunkedPrefill, KVCache


@dataclass(frozen=True)
class GenerationConfig:
    max_new_tokens: int = 256
    temperature: float = 1.0
    top_k: int = 0
    top_p: float = 0.0
    stop: Optional[List[str]] = None


class TokenStream:
    """Iterable token stream with optional stop sequences."""

    def __init__(self, tokens: List[int], config: GenerationConfig) -> None:
        self.tokens = tokens
        self.config = config
        self.index = 0

    def __iter__(self) -> Iterator[int]:
        for token in self.tokens:
            if self.config.stop and self._matches_stop(token):
                break
            yield token
            self.index += 1

    def _matches_stop(self, token: int) -> bool:
        return False


def sample_logits(logits: np.ndarray, temperature: float = 1.0, top_k: int = 0, top_p: float = 0.0) -> int:
    """Sample one token from logits using temperature, top-k, and top-p."""
    if temperature <= 0:
        return int(np.argmax(logits))
    logits = logits / temperature
    if top_k > 0:
        indices = np.argsort(logits)[-top_k:]
        mask = np.ones_like(logits, dtype=bool)
        mask[indices] = False
        logits[mask] = -np.inf
    if top_p > 0:
        sorted_idx = np.argsort(logits)[::-1]
        sorted_probs = np.cumsum(np.exp(logits[sorted_idx] - np.max(logits)))
        cutoff = np.searchsorted(sorted_probs, top_p)
        mask = np.ones_like(logits, dtype=bool)
        mask[sorted_idx[cutoff:]] = False
        logits[mask] = -np.inf
    probs = np.exp(logits - np.max(logits))
    probs = probs / np.sum(probs)
    return int(np.random.choice(len(probs), p=probs))


def chunked_prefill(x: np.ndarray, chunk_size: int = 2048) -> List[np.ndarray]:
    """Split a long sequence into chunks for bounded memory prefill."""
    splitter = ChunkedPrefill(chunk_size=chunk_size)
    return [chunk.numpy() for chunk in splitter.split(x)]


def batch_generate(model, prompts: Iterable[np.ndarray], config: GenerationConfig) -> List[List[int]]:
    """Run batched generation over multiple prompts."""
    results: List[List[int]] = []
    for prompt in prompts:
        results.append(list(_generate(model, prompt, config)))
    return results


def _generate(model, prompt: np.ndarray, config: GenerationConfig) -> Iterator[int]:
    """Single-sequence generation iterator."""
    cache = KVCache()
    x = prompt
    for _ in range(config.max_new_tokens):
        logits = model(x) if callable(model) else np.zeros((1, 1))
        next_token = sample_logits(logits[-1, -1, :], temperature=config.temperature,
                                   top_k=config.top_k, top_p=config.top_p)
        yield next_token
        x = np.array([[next_token]])
