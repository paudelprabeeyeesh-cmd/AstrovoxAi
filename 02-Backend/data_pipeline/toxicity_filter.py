import re
from typing import Any

import numpy as np


class ToxicityFilter:
    def __init__(self, lexicon: dict[str, float] | None = None) -> None:
        self.lexicon = lexicon or {
            "hate": 0.8,
            "abuse": 0.7,
            "harm": 0.9,
            "kill": 0.6,
            "toxic": 0.9,
        }

    def score(self, text: str) -> float:
        words = re.findall(r"\w+", text.lower())
        if not words:
            return 0.0
        scores = [self.lexicon.get(w, 0.0) for w in words]
        return float(np.mean(scores))

    def down_weight(self, text: str, base_weight: float = 1.0, high_cutoff: float = 0.6, low_cutoff: float = 0.2) -> float:
        s = self.score(text)
        if s >= high_cutoff:
            return base_weight * 0.1
        if s <= low_cutoff:
            return base_weight * 1.0
        return base_weight * (1.0 - s)
