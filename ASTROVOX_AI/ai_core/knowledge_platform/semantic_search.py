"""AI semantic search."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AISearchQuery:
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 10


@dataclass
class AISearchResult:
    id: str
    score: float
    payload: Dict[str, Any]


class AISemanticSearch:
    def __init__(self) -> None:
        self._index: List[Dict[str, Any]] = []

    def index(self, documents: List[Dict[str, Any]]) -> None:
        self._index.extend(documents)

    def search(self, query: str, limit: int = 10) -> List[AISearchResult]:
        results = []
        for doc in self._index:
            score = str(doc).lower().count(query.lower())
            results.append(AISearchResult(id=doc.get("id", ""), score=score, payload=doc))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]


ai_semantic_search = AISemanticSearch()
