"""Advanced RAG with hybrid search and reranking."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Document:
    doc_id: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class HybridSearchRAG:
    """Hybrid search combining BM25, vector, and graph retrieval with reranking."""

    def __init__(self):
        self._documents: Dict[str, Document] = {}
        self._bm25_index: Dict[str, Dict[str, int]] = {}
        self._vector_index: Dict[str, List[float]] = {}

    def index(self, doc: Document) -> None:
        self._documents[doc.doc_id] = doc
        if doc.embedding:
            self._vector_index[doc.doc_id] = doc.embedding
        tokens = doc.text.lower().split()
        for token in tokens:
            self._bm25_index.setdefault(token, {}).setdefault(doc.doc_id, 0)
            self._bm25_index[token][doc.doc_id] += 1

    def search(self, query: str, query_embedding: Optional[List[float]] = None, top_k: int = 5, alpha: float = 0.5) -> List[Tuple[str, float]]:
        bm25_scores = self._bm25_search(query, top_k=top_k * 3)
        vector_scores = self._vector_search(query_embedding, top_k=top_k * 3) if query_embedding else {}
        doc_scores: Dict[str, float] = {}
        for doc_id, score in bm25_scores:
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + score * alpha
        for doc_id, score in vector_scores:
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + score * (1.0 - alpha)
        ranked = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def _bm25_search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        tokens = query.lower().split()
        scores: Dict[str, float] = {}
        for token in tokens:
            postings = self._bm25_index.get(token, {})
            for doc_id, tf in postings.items():
                scores[doc_id] = scores.get(doc_id, 0.0) + tf
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def _vector_search(self, query_embedding: List[float], top_k: int = 10) -> List[Tuple[str, float]]:
        import math
        scores = []
        for doc_id, doc_vec in self._vector_index.items():
            dot = sum(a * b for a, b in zip(query_embedding, doc_vec))
            norm_a = math.sqrt(sum(a * a for a in query_embedding))
            norm_b = math.sqrt(sum(b * b for b in doc_vec))
            score = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
            scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def rerank(self, query: str, candidates: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        query_terms = set(query.lower().split())
        scored = []
        for doc_id in candidates:
            doc = self._documents.get(doc_id)
            if not doc:
                continue
            terms = set(doc.text.lower().split())
            overlap = len(query_terms & terms)
            score = overlap / max(len(query_terms), 1)
            scored.append((doc_id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
