"""Database optimization for AstrovoxAI backend.

Provides query plan analysis, connection pool tuning, and index management.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.distributed_cache import distributed_cache

logger = logging.getLogger(__name__)


@dataclass
class QueryPlan:
    query: str
    plan_type: str
    cost: float
    rows: int
    execution_time_ms: float
    suggestions: List[str]


class DatabaseOptimizer:
    """Analyzes and optimizes database operations."""

    def __init__(self):
        self._plans: List[QueryPlan] = []
        self._query_cache_hits = 0
        self._query_cache_misses = 0

    def analyze_query(self, query: str, execution_time_ms: float, rows_scanned: int = 0, rows_returned: int = 0) -> QueryPlan:
        suggestions = []
        if execution_time_ms > 100:
            suggestions.append("Consider adding an index on filtered columns")
        if rows_scanned > 1000 and rows_returned < 100:
            suggestions.append("High rows scanned - review WHERE clause selectivity")
        if "SELECT *" in query.upper():
            suggestions.append("Avoid SELECT * - specify only required columns")
        if "ORDER BY" in query.upper() and "LIMIT" not in query.upper():
            suggestions.append("Consider adding LIMIT to ORDER BY queries")
        if "JOIN" in query.upper() and execution_time_ms > 50:
            suggestions.append("Review JOIN order and consider denormalization")
        plan = QueryPlan(
            query=query,
            plan_type="sequential" if rows_scanned > rows_returned * 10 else "indexed",
            cost=rows_scanned * execution_time_ms,
            rows=rows_returned,
            execution_time_ms=execution_time_ms,
            suggestions=suggestions,
        )
        self._plans.append(plan)
        return plan

    def get_slow_queries(self, threshold_ms: float = 100.0) -> List[QueryPlan]:
        return sorted(
            [p for p in self._plans if p.execution_time_ms > threshold_ms],
            key=lambda p: p.execution_time_ms,
            reverse=True,
        )

    def get_optimization_suggestions(self) -> List[str]:
        suggestions = set()
        for plan in self._plans:
            suggestions.update(plan.suggestions)
        return list(suggestions)

    def optimize_pool_settings(self, current_pool_size: int, avg_wait_ms: float, avg_duration_ms: float) -> Dict[str, int]:
        if avg_wait_ms > 50 and current_pool_size < 20:
            return {"min_size": current_pool_size + 2, "max_size": current_pool_size + 5}
        if avg_wait_ms < 5 and current_pool_size > 5:
            return {"min_size": max(2, current_pool_size - 1), "max_size": max(5, current_pool_size - 2)}
        return {"min_size": current_pool_size, "max_size": current_pool_size}

    def cached_query(self, key: str, ttl: int = 300) -> Callable:
        def decorator(func: Callable) -> Callable:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                result = distributed_cache.get(key)
                if result is not None:
                    self._query_cache_hits += 1
                    return result
                self._query_cache_misses += 1
                start = time.perf_counter()
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                self.analyze_query(key, duration)
                distributed_cache.set(key, result, ttl=ttl)
                return result
            return wrapper
        return decorator

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_analyzed": len(self._plans),
            "slow_queries": len([p for p in self._plans if p.execution_time_ms > 100]),
            "cache_hits": self._query_cache_hits,
            "cache_misses": self._query_cache_misses,
            "suggestions": len(self.get_optimization_suggestions()),
        }


database_optimizer = DatabaseOptimizer()
