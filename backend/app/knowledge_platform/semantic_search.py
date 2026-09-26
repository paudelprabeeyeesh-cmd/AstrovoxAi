"""Semantic search for knowledge platform."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 10


@dataclass
class SearchResult:
    id: str
    score: float
    payload: Dict[str, Any]


class SemanticSearch:
    def __init__(self) -> None:
        self._index: List[Dict[str, Any]] = []

    def index(self, documents: List[Dict[str, Any]]) -> None:
        self._index.extend(documents)

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        results = []
        for doc in self._index:
            score = self._score(query, doc)
            results.append(SearchResult(id=doc.get("id", ""), score=score, payload=doc))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _score(self, query: str, doc: Dict[str, Any]) -> float:
        text = str(doc)
        return text.lower().count(query.lower())


semantic_search = SemanticSearch()
