"""Query optimization for database operations in AstrovoxAI.

Provides query analysis, index suggestions, and query result caching.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.distributed_cache import distributed_cache

logger = logging.getLogger(__name__)


@dataclass
class QueryProfile:
    query_hash: str
    query: str
    execution_time_ms: float
    rows_scanned: int
    rows_returned: int
    timestamp: float
    slow: bool = False


class QueryOptimizer:
    """Analyzes and optimizes database queries."""

    def __init__(self, slow_query_threshold_ms: float = 100.0):
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self._profiles: List[QueryProfile] = []
        self._index_suggestions: Dict[str, List[str]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def profile_query(self, query: str, duration_ms: float, rows_scanned: int = 0, rows_returned: int = 0) -> QueryProfile:
        query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
        profile = QueryProfile(
            query_hash=query_hash,
            query=query,
            execution_time_ms=duration_ms,
            rows_scanned=rows_scanned,
            rows_returned=rows_returned,
            timestamp=time.time(),
            slow=duration_ms > self.slow_query_threshold_ms,
        )
        self._profiles.append(profile)
        if profile.slow:
            logger.warning(
                "Slow query detected: %.2fms - %s",
                duration_ms,
                query[:120],
            )
            self._suggest_index(query, profile)
        return profile

    def _suggest_index(self, query: str, profile: QueryProfile) -> None:
        suggestions = []
        tables = ["profiles", "conversations", "messages", "ai_memory", "user_settings"]
        for table in tables:
            if f"WHERE {table}." in query or f"FROM {table}" in query:
                suggestions.append(f"CREATE INDEX idx_{table}_opt ON {table} (user_id, created_at)")
        if suggestions:
            self._index_suggestions[profile.query_hash] = suggestions

    def get_slow_queries(self, limit: int = 20) -> List[QueryProfile]:
        return sorted(
            [p for p in self._profiles if p.slow],
            key=lambda p: p.execution_time_ms,
            reverse=True,
        )[:limit]

    def get_index_suggestions(self) -> Dict[str, List[str]]:
        return dict(self._index_suggestions)

    def cached_query(self, cache_key: str, ttl: int = 300) -> Callable:
        def decorator(func: Callable) -> Callable:
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                result = distributed_cache.get(cache_key)
                if result is not None:
                    self._cache_hits += 1
                    return result
                self._cache_misses += 1
                start = time.perf_counter()
                result = await func(*args, **kwargs) if asyncio_iscoroutine(func) else func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                self.profile_query(cache_key, duration)
                distributed_cache.set(cache_key, result, ttl=ttl)
                return result
            return wrapper
        return decorator

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_profiles": len(self._profiles),
            "slow_queries": len(self._profiles),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": self._cache_hits / max(self._cache_hits + self._cache_misses, 1),
            "index_suggestions": sum(len(v) for v in self._index_suggestions.values()),
        }


def asyncio_iscoroutine(func: Any) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(func)


query_optimizer = QueryOptimizer()
