import hashlib
from typing import Any

import numpy as np


class Decontaminator:
    def __init__(self, n: int = 5) -> None:
        self.n = n

    def _ngrams(self, text: str) -> list[str]:
        text = text.lower()
        return [text[i : i + self.n] for i in range(max(len(text) - self.n + 1, 0))]

    def _hash_ngrams(self, ngrams: list[str]) -> np.ndarray:
        return np.array([int(hashlib.md5(g.encode()).hexdigest()[:8], 16) for g in ngrams], dtype=np.uint64)

    def overlap(self, text: str, benchmarks: list[str]) -> np.ndarray:
        text_ngrams = self.hash_ngrams(self._ngrams(text))
        results = np.zeros(len(benchmarks), dtype=np.float32)
        for i, b in enumerate(benchmarks):
            b_ngrams = self.hash_ngrams(self._ngrams(b))
            if text_ngrams.size == 0 or b_ngrams.size == 0:
                results[i] = 0.0
            else:
                inter = np.intersect1d(text_ngrams, b_ngrams, assume_unique=False)
                results[i] = len(inter) / max(len(b_ngrams), 1)
        return results

    @staticmethod
    def hash_ngrams(ngrams: list[str]) -> np.ndarray:
        return np.array([int(hashlib.md5(g.encode()).hexdigest()[:8], 16) for g in ngrams], dtype=np.uint64)
