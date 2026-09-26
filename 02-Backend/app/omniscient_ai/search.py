"""Omniscient Search - Searches across all data in the universe."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    result_id: str
    content: str
    score: float
    source: str = "omniscient"
    metadata: Dict[str, Any] = field(default_factory=dict)
    reality_layer: int = 0
    timestamp: float = field(default_factory=time.time)


class OmniscientSearch:
    """Searches across all data, all realities, all timelines."""

    def __init__(self, knowledge_graph=None):
        self._knowledge_graph = knowledge_graph
        self._index: Dict[str, List[SearchResult]] = defaultdict(list)
        self._reality_layers: Dict[int, List[str]] = defaultdict(list)
        self._search_history: List[Dict[str, Any]] = []

    def index_content(self, content: str, metadata: Dict[str, Any] = None, reality_layer: int = 0) -> str:
        result_id = str(uuid.uuid4())
        result = SearchResult(
            result_id=result_id,
            content=content,
            score=1.0,
            source=metadata.get("source", "omniscient") if metadata else "omniscient",
            metadata=metadata or {},
            reality_layer=reality_layer,
        )
        self._index[content.lower()].append(result)
        self._reality_layers[reality_layer].append(result_id)
        return result_id

    def search(self, query: str, reality_layers: Optional[List[int]] = None, limit: int = 20) -> List[SearchResult]:
        query_lower = query.lower()
        results = []
        for content, result_list in self._index.items():
            if query_lower in content:
                for r in result_list:
                    if reality_layers is None or r.reality_layer in reality_layers:
                        results.append(r)
        results.sort(key=lambda x: x.score, reverse=True)
        self._search_history.append({
            "query": query,
            "timestamp": time.time(),
            "results_count": len(results),
        })
        return results[:limit]

    def cross_reality_search(self, query: str, limit: int = 20) -> List[SearchResult]:
        return self.search(query, reality_layers=None, limit=limit)

    def get_search_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._search_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "indexed_items": sum(len(v) for v in self._index.values()),
            "reality_layers": len(self._reality_layers),
            "search_history_count": len(self._search_history),
        }
