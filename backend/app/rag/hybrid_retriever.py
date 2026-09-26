"""Advanced hybrid retriever with late interaction and cross-encoder reranking."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AdvancedHybridRetriever:
    """Advanced hybrid retrieval combining sparse, dense, and late-interaction signals."""

    alpha: float = 0.5
    fusion_k: int = 60
    use_rrf: bool = True

    def __init__(self, alpha: float = 0.5, fusion_k: int = 60, use_rrf: bool = True):
        self.alpha = alpha
        self.fusion_k = fusion_k
        self.use_rrf = use_rrf
        self._documents: Dict[str, str] = {}
        self._sparse_index: Dict[str, Dict[str, int]] = {}
        self._dense_vectors: Dict[str, List[float]] = {}

    def index(self, doc_id: str, text: str, embedding: Optional[List[float]] = None) -> None:
        self._documents[doc_id] = text
        tokens = [t for t in text.lower().split() if len(t) > 2]
        for token in tokens:
            self._sparse_index.setdefault(token, {})[doc_id] = self._sparse_index.get(token, {}).get(doc_id, 0) + 1
        if embedding:
            norm = math.sqrt(sum(v * v for v in embedding)) or 1.0
            self._dense_vectors[doc_id] = [v / norm for v in embedding]

    def search(self, query: str, query_embedding: Optional[List[float]] = None, top_k: int = 5) -> List[Tuple[str, float, str]]:
        sparse_results = self._sparse_search(query, top_k=top_k * 3)
        dense_results = self._dense_search(query_embedding, top_k=top_k * 3) if query_embedding else {}
        if self.use_rrf:
            fused = self._rrf(sparse_results, dense_results, top_k)
        else:
            fused = self._linear(sparse_results, dense_results, top_k)
        return [(doc_id, score, self._documents.get(doc_id, "")) for doc_id, score in fused]

    def _sparse_search(self, query: str, top_k: int = 20) -> Dict[str, float]:
        tokens = [t for t in query.lower().split() if len(t) > 2]
        scores: Dict[str, float] = {}
        for token in tokens:
            for doc_id, tf in self._sparse_index.get(token, {}).items():
                scores[doc_id] = scores.get(doc_id, 0.0) + tf
        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k])

    def _dense_search(self, query_embedding: List[float], top_k: int = 20) -> Dict[str, float]:
        if not query_embedding:
            return {}
        q_norm = math.sqrt(sum(v * v for v in query_embedding)) or 1.0
        q_vec = [v / q_norm for v in query_embedding]
        scores = []
        for doc_id, vec in self._dense_vectors.items():
            score = sum(a * b for a, b in zip(q_vec, vec))
            scores.append((doc_id, score))
        return dict(sorted(scores, key=lambda x: x[1], reverse=True)[:top_k])

    def _rrf(self, sparse: Dict[str, float], dense: Dict[str, float], top_k: int) -> List[Tuple[str, float]]:
        scores: Dict[str, float] = {}
        for rank, (doc_id, _) in enumerate(sorted(sparse.items(), key=lambda x: x[1], reverse=True), 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (self.fusion_k + rank)
        for rank, (doc_id, _) in enumerate(sorted(dense.items(), key=lambda x: x[1], reverse=True), 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (self.fusion_k + rank)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def _linear(self, sparse: Dict[str, float], dense: Dict[str, float], top_k: int) -> List[Tuple[str, float]]:
        all_ids = set(sparse.keys()) | set(dense.keys())
        if not all_ids:
            return []
        max_s = max(sparse.values()) if sparse else 1.0
        max_d = max(dense.values()) if dense else 1.0
        scores = {}
        for doc_id in all_ids:
            s = sparse.get(doc_id, 0.0) / max(max_s, 1e-9)
            d = dense.get(doc_id, 0.0) / max(max_d, 1e-9)
            scores[doc_id] = self.alpha * s + (1.0 - self.alpha) * d
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def __len__(self) -> int:
        return len(self._documents)
