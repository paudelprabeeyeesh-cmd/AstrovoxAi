"""AI-powered indexing recommendations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class IndexSuggestion:
    table: str
    columns: List[str]
    index_type: str
    estimated_benefit: float
    reason: str


class AIIndexingEngine:
    def __init__(self, query_log: Optional[List[Dict[str, Any]]] = None):
        self._query_log = query_log or []
        self._recommendations: List[IndexSuggestion] = []

    def analyze_workload(self, queries: List[Dict[str, Any]]) -> List[IndexSuggestion]:
        column_freq: Dict[str, int] = {}
        for query in queries:
            for column in query.get("columns", []):
                table_col = f"{query.get('table', 'unknown')}.{column}"
                column_freq[table_col] = column_freq.get(table_col, 0) + 1

        suggestions = []
        for table_col, freq in sorted(column_freq.items(), key=lambda x: x[1], reverse=True):
            table, column = table_col.split(".", 1)
            suggestions.append(
                IndexSuggestion(
                    table=table,
                    columns=[column],
                    index_type="btree",
                    estimated_benefit=min(freq / 100.0, 1.0),
                    reason=f"Column {column} appears in {freq} queries",
                )
            )
        self._recommendations = suggestions
        logger.info("Generated %s index recommendations", len(suggestions))
        return suggestions

    def recommend(self, table: str, sample_data: List[Dict[str, Any]]) -> List[IndexSuggestion]:
        columns = list(sample_data[0].keys()) if sample_data else []
        suggestions = [
            IndexSuggestion(
                table=table,
                columns=columns[:2],
                index_type="btree",
                estimated_benefit=0.8,
                reason="Composite index on top columns for table " + table,
            )
        ]
        return suggestions

    def get_recommendations(self) -> List[IndexSuggestion]:
        return list(self._recommendations)
