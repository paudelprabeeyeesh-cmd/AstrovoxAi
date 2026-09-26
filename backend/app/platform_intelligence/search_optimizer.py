"""Search optimizer for query performance."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    query: str
    results: List[Dict[str, Any]]
    latency_ms: float
    cached: bool = False


class SearchOptimizer:
    def __init__(self) -> None:
        self._cache: Dict[str, SearchResult] = {}

    def search(self, query: str, fetcher: Any, ttl_seconds: float = 300.0) -> SearchResult:
        cached = self._cache.get(query)
        if cached:
            cached.cached = True
            return cached
        results = fetcher(query) if callable(fetcher) else []
        result = SearchResult(query=query, results=results, latency_ms=0.0)
        self._cache[query] = result
        return result

    def invalidate(self, query: str) -> None:
        self._cache.pop(query, None)


search_optimizer = SearchOptimizer()
