"""Memory retrieval for intelligent recall."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    record_id: str
    score: float
    content: str


class MemoryRetriever:
    def __init__(self) -> None:
        self._records: List[Dict[str, Any]] = []

    def index(self, records: List[Dict[str, Any]]) -> None:
        self._records.extend(records)

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        scored = []
        for record in self._records:
            content = str(record.get("content", ""))
            score = content.lower().count(query.lower())
            scored.append(RetrievalResult(record_id=record.get("id", ""), score=score, content=content))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]


memory_retriever = MemoryRetriever()
