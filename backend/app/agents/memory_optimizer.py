from typing import Any, Dict, List, Optional
import logging
import time
import math

logger = logging.getLogger(__name__)


class MemoryOptimizer:
    def __init__(self, max_short_term: int = 100, compaction_threshold: float = 0.8, importance_decay: float = 0.95):
        self.max_short_term = max_short_term
        self.compaction_threshold = compaction_threshold
        self.importance_decay = importance_decay
        self.access_counts: Dict[str, int] = {}
        self.importance_scores: Dict[str, float] = {}
        self.last_access: Dict[str, float] = {}
        self.semantic_clusters: Dict[str, List[str]] = {}

    def _key(self, item: Dict[str, Any]) -> str:
        return str(item)

    def _compute_importance(self, key: str, recency: float) -> float:
        access = self.access_counts.get(key, 0)
        importance = self.importance_scores.get(key, 0.0)
        return (access * 0.3) + (importance * 0.5) + (recency * 0.2)

    def record_access(self, item: Dict[str, Any], boost: float = 1.0) -> None:
        key = self._key(item)
        self.access_counts[key] = self.access_counts.get(key, 0) + 1
        self.importance_scores[key] = min(1.0, self.importance_scores.get(key, 0.0) + boost)
        self.last_access[key] = time.time()

    def decay_importance(self) -> None:
        now = time.time()
        for key in list(self.importance_scores.keys()):
            last = self.last_access.get(key, now)
            elapsed = max(0.0, now - last)
            decay = self.importance_decay ** (elapsed / 3600.0)
            self.importance_scores[key] = max(0.0, self.importance_scores.get(key, 0.0) * decay)

    def optimize(self, short_term: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(short_term) <= self.max_short_term:
            return short_term
        self.decay_importance()
        scored = []
        now = time.time()
        for idx, item in enumerate(short_term):
            key = self._key(item)
            recency = 1.0 / (len(short_term) - idx + 1)
            score = self._compute_importance(key, recency)
            scored.append((item, score, key))
        scored.sort(key=lambda x: x[1], reverse=True)
        optimized = [item for item, _, _ in scored[: self.max_short_term]]
        for item, _, key in scored[self.max_short_term:]:
            self.importance_scores[key] = 0.0
        return optimized

    def should_compact(self, short_term: List[Dict[str, Any]]) -> bool:
        return len(short_term) >= int(self.max_short_term * self.compaction_threshold)

    def cluster(self, items: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        clusters: Dict[str, List[str]] = {}
        for item in items:
            key = self._key(item)
            cluster_id = f"cluster_{hash(key) % 10}"
            clusters.setdefault(cluster_id, []).append(key)
        self.semantic_clusters = clusters
        return clusters

    def get_forgettable(self, short_term: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored = []
        for idx, item in enumerate(short_term):
            key = self._key(item)
            recency = 1.0 / (len(short_term) - idx + 1)
            score = self._compute_importance(key, recency)
            scored.append((item, score))
        scored.sort(key=lambda x: x[1])
        return [item for item, _ in scored[: max(1, len(scored) // 4)]]
