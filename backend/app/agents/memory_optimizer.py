from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class MemoryOptimizer:
    def __init__(self, max_short_term: int = 100, compaction_threshold: float = 0.8):
        self.max_short_term = max_short_term
        self.compaction_threshold = compaction_threshold
        self.access_counts: Dict[str, int] = {}

    def optimize(self, short_term: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(short_term) <= self.max_short_term:
            return short_term
        scored = []
        for idx, item in enumerate(short_term):
            key = str(item)
            score = self.access_counts.get(key, 0)
            recency = 1.0 / (len(short_term) - idx)
            scored.append((item, score + recency))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in scored[: self.max_short_term]]

    def record_access(self, item: Dict[str, Any]) -> None:
        key = str(item)
        self.access_counts[key] = self.access_counts.get(key, 0) + 1

    def should_compact(self, short_term: List[Dict[str, Any]]) -> bool:
        return len(short_term) >= int(self.max_short_term * self.compaction_threshold)
