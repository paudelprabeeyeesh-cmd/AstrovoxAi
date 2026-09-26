"""Cross-encoder reranker for RAG."""

from __future__ import annotations

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder style reranker for retrieved documents."""

    def rerank(self, query: str, documents: List[Any], top_k: int = 5) -> List[Tuple[int, float]]:
        scores = []
        for idx, doc in enumerate(documents):
            text = doc.get("text", doc) if isinstance(doc, dict) else doc
            score = self._score(query, text)
            scores.append((idx, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _score(self, query: str, document: str) -> float:
        query_terms = set(query.lower().split())
        doc_terms = set(str(document).lower().split())
        overlap = len(query_terms & doc_terms)
        coverage = overlap / max(len(query_terms), 1)
        density = overlap / max(len(doc_terms), 1)
        return coverage * 0.7 + density * 0.3
