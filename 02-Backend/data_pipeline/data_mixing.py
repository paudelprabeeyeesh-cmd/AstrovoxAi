import re
from typing import Any

import numpy as np


class DataMixer:
    def __init__(self, source_weights: dict[str, float] | None = None) -> None:
        self.source_weights = source_weights or {}

    def tune(self, source_weights: dict[str, float]) -> None:
        self.source_weights = source_weights

    def sample(self, sources: dict[str, list[Any]], n: int) -> list[Any]:
        weights = []
        for src, samples in sources.items():
            w = self.source_weights.get(src, 1.0)
            weights.extend([w] * len(samples))
        all_items = [item for samples in sources.values() for item in samples]
        if not all_items:
            return []
        probs = np.array(weights, dtype=np.float32)
        probs = probs / probs.sum()
        idx = np.random.choice(len(all_items), size=min(n, len(all_items)), p=probs, replace=False)
        return [all_items[i] for i in idx]
