"""Hybrid SQL + vector search integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.app.database.vector_optimization import VectorIndexOptimizer, VectorIndexConfig

logger = logging.getLogger(__name__)


@dataclass
class HybridQuery:
    sql: str
    vector: List[float]
    vector_weight: float = 0.5
    top_k: int = 10
    metadata_filter: Optional[Dict[str, Any]] = None


class HybridSearchEngine:
    def __init__(self, optimizer: VectorIndexOptimizer):
        self._vector_index = optimizer
        self._sql_results: Dict[str, Dict[str, Any]] = {}

    def index_sql_row(self, row_id: str, metadata: Dict[str, Any]) -> None:
        self._sql_results[row_id] = metadata

    def search(self, query: HybridQuery) -> List[Dict[str, Any]]:
        vector_results = self._vector_index.search(query.vector, k=query.top_k * 2)
        scored = []
        for vid, distance in vector_results:
            sql_meta = self._sql_results.get(vid, {})
            vector_score = 1.0 / (1.0 + distance)
            sql_score = sql_meta.get("_score", 0.0)
            combined = query.vector_weight * vector_score + (1.0 - query.vector_weight) * sql_score
            if query.metadata_filter:
                if not all(sql_meta.get(k) == v for k, v in query.metadata_filter.items()):
                    continue
            scored.append({"id": vid, "score": combined, "vector_score": vector_score, "sql_score": sql_score, "metadata": sql_meta})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[: query.top_k]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "indexed_rows": len(self._sql_results),
            "vector_index": self._vector_index.get_stats(),
        }
