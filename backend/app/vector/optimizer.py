"""Vector index optimizer for search performance."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class IndexStats:
    index_name: str
    dimension: int
    total_vectors: int
    avg_latency_ms: float
    p99_latency_ms: float
    recall: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class VectorIndexOptimizer:
    def __init__(self) -> None:
        self._indexes: Dict[str, Any] = {}
        self._stats: Dict[str, List[IndexStats]] = {}

    def register_index(self, index_name: str, dimension: int, config: Optional[Dict[str, Any]] = None) -> None:
        self._indexes[index_name] = {"dimension": dimension, "config": config or {}}
        logger.info("Registered vector index %s with dimension %d", index_name, dimension)

    def optimize(self, index_name: str, strategy: str = "auto") -> Dict[str, Any]:
        index = self._indexes.get(index_name)
        if not index:
            raise ValueError(f"Unknown index: {index_name}")
        if strategy == "auto":
            if index["dimension"] > 256:
                strategy = "ivf_pq"
            else:
                strategy = "hnsw"
        logger.info("Optimizing index %s with strategy %s", index_name, strategy)
        return {"index_name": index_name, "strategy": strategy, "applied": True}

    def record_stats(self, stats: IndexStats) -> None:
        self._stats.setdefault(stats.index_name, []).append(stats)

    def get_recommendations(self, index_name: str) -> List[str]:
        stats = self._stats.get(index_name, [])
        if not stats:
            return ["Insufficient data for recommendations"]
        latest = stats[-1]
        recs = []
        if latest.avg_latency_ms > 100:
            recs.append("Consider using HNSW index for lower latency")
        if latest.recall < 0.9:
            recs.append("Increase nprobe or ef_search to improve recall")
        if latest.p99_latency_ms > 500:
            recs.append("Enable quantization for faster approximate search")
        return recs or ["Index appears healthy"]


vector_index_optimizer = VectorIndexOptimizer()
