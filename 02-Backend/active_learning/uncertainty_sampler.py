import math
import random
from typing import List, Sequence, Dict, Any, Optional

from .query_strategy import QueryStrategy


class UncertaintySampler:
    def __init__(self, strategy: str = QueryStrategy.UNCERTAINTY):
        QueryStrategy.validate(strategy)
        self.strategy = strategy
        self._query_log: List[Dict[str, Any]] = []

    def _entropy(self, proba: Sequence[float]) -> float:
        return -sum(p * math.log(p + 1e-12) for p in proba if p > 0)

    def _margin(self, proba: Sequence[float]) -> float:
        sorted_p = sorted(proba, reverse=True)
        return sorted_p[0] - sorted_p[1] if len(sorted_p) >= 2 else 0.0

    def score(self, proba: Sequence[float]) -> float:
        if self.strategy == QueryStrategy.UNCERTAINTY:
            return 1.0 - max(proba)
        elif self.strategy == QueryStrategy.ENTROPY:
            return self._entropy(proba)
        elif self.strategy == QueryStrategy.MARGIN:
            return self._margin(proba)
        elif self.strategy == QueryStrategy.RANDOM:
            return random.random()
        elif self.strategy == QueryStrategy.EXPECTED_LEARNING_GAIN:
            return self._entropy(proba)
        raise ValueError(f"Unknown strategy: {self.strategy}")

    def sample_indices(
        self, probas: List[Sequence[float]], batch_size: int
    ) -> List[int]:
        scores = [self.score(p) for p in probas]

        if self.strategy in (QueryStrategy.ENTROPY, QueryStrategy.UNCERTAINTY, QueryStrategy.EXPECTED_LEARNING_GAIN):
            ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        elif self.strategy == QueryStrategy.MARGIN:
            ranked = sorted(range(len(scores)), key=lambda i: scores[i])
        else:
            ranked = list(range(len(scores)))
            random.shuffle(ranked)

        selected = ranked[: min(batch_size, len(ranked))]

        for idx in selected:
            self._query_log.append(
                {"index": idx, "score": scores[idx], "strategy": self.strategy}
            )

        return selected

    def get_query_log(self) -> List[Dict[str, Any]]:
        return list(self._query_log)

    def clear_log(self) -> None:
        self._query_log = []
