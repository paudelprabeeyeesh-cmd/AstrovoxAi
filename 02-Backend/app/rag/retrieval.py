"""Hybrid and multi-query retrieval for RAG pipelines."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    chunk_id: str
    document_id: str
    content: str
    score: float
    source: str = "hybrid"
    metadata: Dict[str, Any] = field(default_factory=dict)
    highlights: List[str] = field(default_factory=list)


class BM25SparseIndex:
    """Simple BM25 sparse index for keyword retrieval."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._postings: Dict[str, Dict[str, int]] = {}
        self._doc_lengths: Dict[str, int] = {}
        self._avg_dl: float = 0.0
        self._doc_count: int = 0

    def add(self, doc_id: str, text: str) -> None:
        tokens = self._tokenize(text)
        self._doc_lengths[doc_id] = len(tokens)
        for token in tokens:
            self._postings.setdefault(token, {})[doc_id] = self._postings.get(token, {}).get(doc_id, 0) + 1
        self._doc_count = len(self._doc_lengths)
        self._avg_dl = sum(self._doc_lengths.values()) / max(self._doc_count, 1)

    def add_batch(self, items: List[Tuple[str, str]]) -> None:
        for doc_id, text in items:
            self.add(doc_id, text)

    def search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        tokens = self._tokenize(query)
        scores: Dict[str, float] = {}
        for token in tokens:
            postings = self._postings.get(token, {})
            df = len(postings)
            idf = math.log((self._doc_count - df + 0.5) / (df + 0.5) + 1.0)
            for doc_id, tf in postings.items():
                dl = self._doc_lengths.get(doc_id, self._avg_dl or 1)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / max(self._avg_dl, 1))
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * numerator / max(denominator, 1e-9)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [t for t in __import__("re").findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower()) if len(t) >= 2]

    @property
    def size(self) -> int:
        return self._doc_count


class DenseVectorIndex:
    """Simple dense vector index with cosine similarity."""

    def __init__(self):
        self._vectors: Dict[str, List[float]] = {}
        self._documents: Dict[str, str] = {}

    def add(self, doc_id: str, embedding: List[float], text: str = "") -> None:
        norm = math.sqrt(sum(v * v for v in embedding)) or 1.0
        self._vectors[doc_id] = [v / norm for v in embedding]
        if text:
            self._documents[doc_id] = text

    def add_batch(self, items: List[Tuple[str, List[float], str]]) -> None:
        for doc_id, embedding, text in items:
            self.add(doc_id, embedding, text)

    def search(self, query_embedding: List[float], top_k: int = 20) -> List[Tuple[str, float]]:
        q_norm = math.sqrt(sum(v * v for v in query_embedding)) or 1.0
        q_vec = [v / q_norm for v in query_embedding]
        scores = []
        for doc_id, vec in self._vectors.items():
            score = sum(a * b for a, b in zip(q_vec, vec))
            scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    @property
    def size(self) -> int:
        return len(self._vectors)


class HybridRetriever:
    """Feature: Hybrid retrieval combining BM25 sparse and dense vector search with RRF fusion."""

    def __init__(self, alpha: float = 0.5, fusion: str = "linear"):
        self.alpha = alpha
        self.fusion = fusion
        self.bm25 = BM25SparseIndex()
        self.vector = DenseVectorIndex()
        self._documents: Dict[str, str] = {}

    def index(self, doc_id: str, text: str, embedding: Optional[List[float]] = None) -> None:
        self._documents[doc_id] = text
        self.bm25.add(doc_id, text)
        if embedding:
            self.vector.add(doc_id, embedding, text)

    def search(self, query: str, query_embedding: Optional[List[float]] = None,
               top_k: int = 5, alpha: Optional[float] = None) -> List[RetrievalResult]:
        alpha = alpha if alpha is not None else self.alpha
        bm25_results = dict(self.bm25.search(query, top_k=top_k * 3))
        vector_results = dict(self.vector.search(query_embedding, top_k=top_k * 3)) if query_embedding else {}

        if self.fusion == "rrf":
            fused = self._rrf_fusion(bm25_results, vector_results, top_k)
        else:
            fused = self._linear_fusion(bm25_results, vector_results, top_k, alpha)

        return [
            RetrievalResult(chunk_id=doc_id, document_id=doc_id, content=self._documents.get(doc_id, ""),
                            score=score, source="hybrid")
            for doc_id, score in fused if score > 0
        ]

    def _linear_fusion(self, bm25: Dict[str, float], vector: Dict[str, float],
                       top_k: int, alpha: float) -> List[Tuple[str, float]]:
        all_ids = set(bm25.keys()) | set(vector.keys())
        if not all_ids:
            return []
        max_bm25 = max(bm25.values()) if bm25 else 1.0
        max_vec = max(vector.values()) if vector else 1.0
        scores: Dict[str, float] = {}
        for doc_id in all_ids:
            b = (bm25.get(doc_id, 0.0) / max(max_bm25, 1e-9))
            v = (vector.get(doc_id, 0.0) / max(max_vec, 1e-9))
            scores[doc_id] = alpha * b + (1.0 - alpha) * v
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return ranked

    def _rrf_fusion(self, bm25: Dict[str, float], vector: Dict[str, float],
                    top_k: int, k: int = 60) -> List[Tuple[str, float]]:
        scores: Dict[str, float] = {}
        for rank, (doc_id, _) in enumerate(sorted(bm25.items(), key=lambda x: x[1], reverse=True), 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        for rank, (doc_id, _) in enumerate(sorted(vector.items(), key=lambda x: x[1], reverse=True), 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return ranked

    def __len__(self) -> int:
        return len(self._documents)


class MultiQueryRetriever:
    """Feature: Multi-query retrieval — generate query variations and fuse results."""

    def __init__(self, retriever: Optional[HybridRetriever] = None):
        self.retriever = retriever or HybridRetriever()
        self._synonyms = {
            "search": ["find", "lookup", "retrieve"],
            "create": ["build", "generate", "make", "produce"],
            "analyze": ["examine", "review", "inspect"],
            "help": ["assist", "support", "guide"],
            "error": ["bug", "issue", "problem", "fault"],
            "data": ["information", "content", "records"],
            "model": ["system", "framework", "architecture"],
            "fast": ["quick", "rapid", "speedy"],
            "good": ["great", "excellent", "quality"],
        }

    def retrieve(self, query: str, query_embedding: Optional[List[float]] = None,
                 top_k: int = 5, expansions: int = 3) -> List[RetrievalResult]:
        queries = self._expand(query, expansions)
        candidates: Dict[str, RetrievalResult] = {}
        for q in queries:
            for result in self.retriever.search(q, query_embedding, top_k=top_k * 2):
                if result.chunk_id not in candidates:
                    candidates[result.chunk_id] = result
                else:
                    existing = candidates[result.chunk_id]
                    existing.score = max(existing.score, result.score)
                    existing.metadata = {**existing.metadata, **result.metadata}
        ranked = sorted(candidates.values(), key=lambda r: r.score, reverse=True)
        return ranked[:top_k]

    def _expand(self, query: str, expansions: int) -> List[str]:
        words = [w for w in __import__("re").findall(r"\b[a-zA-Z]{3,}\b", query.lower()) if w not in {
            "the", "and", "is", "of", "to", "in", "that", "for", "with", "as", "on", "at", "by", "an", "a"}]
        queries = [query]
        for word in words[:5]:
            for syn in self._synonyms.get(word, [])[:2]:
                expanded = query.replace(word, syn)
                if expanded not in queries:
                    queries.append(expanded)
        return queries[:expansions + 1]
