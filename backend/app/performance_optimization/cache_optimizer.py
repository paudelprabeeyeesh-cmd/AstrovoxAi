"""Cache optimization for performance."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheHitRate:
    cache_name: str
    hits: int
    misses: int
    hit_rate: float = 0.0
    measured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CacheOptimizer:
    def __init__(self) -> None:
        self._metrics: Dict[str, CacheHitRate] = {}

    def record(self, cache_name: str, hits: int, misses: int) -> CacheHitRate:
        total = hits + misses
        hit_rate = hits / total if total > 0 else 0.0
        metric = CacheHitRate(cache_name=cache_name, hits=hits, misses=misses, hit_rate=hit_rate)
        self._metrics[cache_name] = metric
        return metric

    def get_metric(self, cache_name: str) -> Optional[CacheHitRate]:
        return self._metrics.get(cache_name)


cache_optimizer = CacheOptimizer()
