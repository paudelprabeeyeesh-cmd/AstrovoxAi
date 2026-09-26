"""Cross-encoder reranker for RAG pipelines."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    chunk_id: str
    document_id: str
    content: str
    score: float
    rank: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Reranker:
    """Automatic reranking of retrieved documents using cross-encoder style scoring."""

    def __init__(self, alpha: float = 0.7, beta: float = 0.3):
        self.alpha = alpha
        self.beta = beta

    def rerank(self, query: str, documents: List[Any], top_k: int = 5) -> List[RerankResult]:
        scored: List[tuple[float, int, Any]] = []
        query_terms = set(query.lower().split())
        for idx, doc in enumerate(documents):
            text = doc.get("content", doc) if isinstance(doc, dict) else str(doc)
            doc_terms = set(text.lower().split())
            overlap = len(query_terms & doc_terms)
            coverage = overlap / max(len(query_terms), 1)
            density = overlap / max(len(doc_terms), 1)
            score = self.alpha * coverage + self.beta * density
            scored.append((score, idx, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for rank, (score, idx, doc) in enumerate(scored[:top_k], 1):
            if isinstance(doc, dict):
                results.append(RerankResult(
                    chunk_id=doc.get("chunk_id", str(idx)),
                    document_id=doc.get("document_id", str(idx)),
                    content=doc.get("content", ""),
                    score=score,
                    rank=rank,
                    metadata=doc.get("metadata", {}),
                ))
            else:
                results.append(RerankResult(
                    chunk_id=str(idx),
                    document_id=str(idx),
                    content=str(doc),
                    score=score,
                    rank=rank,
                ))
        return results
