"""Query optimizer with plan caching and hints."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueryPlan:
    query_hash: str
    original_query: str
    optimized_query: str
    estimated_cost: float
    used_index: Optional[str] = None
    hints: List[str] = field(default_factory=list)


class QueryOptimizer:
    def __init__(self):
        self._cache: Dict[str, QueryPlan] = {}
        self._index_stats: Dict[str, Dict[str, Any]] = {}

    def register_index(self, table: str, index_name: str, columns: List[str], selectivity: float = 1.0) -> None:
        self._index_stats.setdefault(table, {})[index_name] = {
            "columns": columns,
            "selectivity": selectivity,
        }

    def optimize(self, query: str, force_hints: Optional[List[str]] = None) -> QueryPlan:
        query_hash = str(hash(query))
        if query_hash in self._cache:
            plan = self._cache[query_hash]
            if force_hints:
                plan.hints = force_hints
            return plan

        hints = force_hints or self._suggest_hints(query)
        optimized = self._rewrite_query(query, hints)
        plan = QueryPlan(
            query_hash=query_hash,
            original_query=query,
            optimized_query=optimized,
            estimated_cost=self._estimate_cost(optimized, hints),
            used_index=hints[0] if hints else None,
            hints=hints,
        )
        self._cache[query_hash] = plan
        logger.debug("Optimized query with hints %s", hints)
        return plan

    def _suggest_hints(self, query: str) -> List[str]:
        hints = []
        for table, indexes in self._index_stats.items():
            if table in query:
                best = min(indexes.items(), key=lambda x: x[1]["selectivity"])
                hints.append(f"INDEX({table} {best[0]})")
        return hints

    def _rewrite_query(self, query: str, hints: List[str]) -> str:
        optimized = query.strip()
        if hints and not optimized.upper().startswith("SELECT"):
            optimized = f"SELECT * FROM ({optimized})"
        if hints:
            optimized += " " + " ".join(hints)
        return optimized

    def _estimate_cost(self, query: str, hints: List[str]) -> float:
        base_cost = len(query) * 0.01
        if "INDEX" in " ".join(hints):
            base_cost *= 0.1
        return base_cost

    def invalidate(self, query_hash: str) -> None:
        self._cache.pop(query_hash, None)

    def get_cache_stats(self) -> Dict[str, Any]:
        return {
            "cached_plans": len(self._cache),
            "index_stats": {
                table: list(indexes.keys()) for table, indexes in self._index_stats.items()
            },
        }
