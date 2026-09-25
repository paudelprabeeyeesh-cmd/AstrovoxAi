"""RAG: cross-encoder reranker skeleton."""

from __future__ import annotations

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class Reranker:
    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[Tuple[int, float]]:
        scores = []
        for idx, doc in enumerate(documents):
            score = self._score(query, doc)
            scores.append((idx, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _score(self, query: str, document: str) -> float:
        query_terms = set(query.lower().split())
        doc_terms = set(document.lower().split())
        return len(query_terms & doc_terms) / max(len(query_terms), 1)
