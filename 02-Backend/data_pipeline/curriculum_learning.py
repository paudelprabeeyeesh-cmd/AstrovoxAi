import re
from typing import Any

import numpy as np


class CurriculumLearner:
    def __init__(self, features: list[str] | None = None) -> None:
        self.features = features or ["length", "vocab_richness", "avg_word_length"]

    def difficulty(self, text: str) -> float:
        words = re.findall(r"\w+", text.lower())
        if not words:
            return 0.0
        length = len(text)
        vocab = len(set(words)) / max(len(words), 1)
        avg_len = np.mean([len(w) for w in words])
        feats = np.array([length / 1000.0, vocab, avg_len / 10.0], dtype=np.float32)
        return float(np.mean(feats))

    def order(self, samples: list[str], ascending: bool = True) -> list[str]:
        diffs = [self.difficulty(s) for s in samples]
        return [s for _, s in sorted(zip(diffs, samples), reverse=not ascending)]
