"""Hybrid RAG: dense + sparse + reranker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class Document:
    id: str
    content: str
    metadata: Dict[str, Any] = None
    embedding: Optional[List[float]] = None


class HybridRAG:
    """Hybrid retrieval-augmented generation pipeline."""

    def __init__(self) -> None:
        self._config = get_config()
        self._documents: Dict[str, Document] = {}
        self._embeddings: Dict[str, List[float]] = {}

    def ingest(self, documents: List[Document]) -> int:
        for doc in documents:
            self._documents[doc.id] = doc
        logger.info(f"Ingested {len(documents)} documents")
        return len(documents)

    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        results = []
        query_lower = query.lower()
        for doc in self._documents.values():
            if query_lower in doc.content.lower():
                results.append(doc)
        results.sort(key=lambda d: len(d.content), reverse=True)
        return results[:top_k]

    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Document]:
        scored = []
        query_terms = set(query.lower().split())
        for doc in documents:
            content_terms = set(doc.content.lower().split())
            score = len(query_terms & content_terms) / max(len(query_terms), 1)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]


_rag: Optional[HybridRAG] = None


def get_rag() -> HybridRAG:
    global _rag
    if _rag is None:
        _rag = HybridRAG()
    return _rag
