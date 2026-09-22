"""
Hybrid RAG: dense retrieval + sparse retrieval (BM25) + RRF fusion + cross-encoder reranking.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Document:
    doc_id: str
    text: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = None


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


def _compute_tf(tokens: List[str]) -> Dict[str, int]:
    tf = {}
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1
    return tf


def _compute_idf(documents: List[List[str]]) -> Dict[str, float]:
    n = len(documents)
    idf = {}
    for doc_tokens in documents:
        for token in set(doc_tokens):
            idf[token] = idf.get(token, 0) + 1
    for token, freq in idf.items():
        idf[token] = math.log((n - freq + 0.5) / (freq + 0.5) + 1)
    return idf


def bm25_score(query: str, documents: List[str], k1: float = 1.5, b: float = 0.75) -> List[Tuple[int, float]]:
    """BM25 sparse retrieval from scratch."""
    doc_tokens = [_tokenize(doc) for doc in documents]
    idf = _compute_idf(doc_tokens)
    avg_dl = sum(len(t) for t in doc_tokens) / max(len(doc_tokens), 1)
    query_tokens = _tokenize(query)
    scores = []
    for idx, tokens in enumerate(doc_tokens):
        tf = _compute_tf(tokens)
        dl = len(tokens)
        score = 0.0
        for token in query_tokens:
            if token not in tf:
                continue
            idf_val = idf.get(token, 0.0)
            tf_val = tf[token]
            score += idf_val * (tf_val * (k1 + 1)) / (tf_val + k1 * (1 - b + b * dl / max(avg_dl, 1)))
        scores.append((idx, score))
    return sorted(scores, key=lambda x: x[1], reverse=True)


def dense_retrieval(query_embedding: np.ndarray, documents: List[Document], top_k: int = 10) -> List[Tuple[int, float]]:
    """Dense retrieval using cosine similarity."""
    scores = []
    for idx, doc in enumerate(documents):
        if doc.embedding is None:
            continue
        sim = cosine_similarity(query_embedding, doc.embedding)
        scores.append((idx, float(sim)))
    return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def reciprocal_rank_fusion(results_list: List[List[Tuple[int, float]]], k: int = 60) -> List[Tuple[int, float]]:
    """Reciprocal Rank Fusion (RRF)."""
    scores: Dict[int, float] = {}
    for results in results_list:
        for rank, (doc_idx, _) in enumerate(results):
            scores[doc_idx] = scores.get(doc_idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class CrossEncoderReranker:
    """Simple 2-layer neural network for reranking."""

    def __init__(self, embedding_dim: Optional[int] = None, hidden_dim: int = 32):
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.w1 = None
        self.b1 = None
        self.w2 = None
        self.b2 = None
        self._initialized = False

    def _ensure_init(self, input_dim: int):
        if not self._initialized or self.embedding_dim != input_dim:
            self.embedding_dim = input_dim
            self.w1 = np.random.randn(input_dim * 2, self.hidden_dim) * 0.01
            self.b1 = np.zeros(self.hidden_dim)
            self.w2 = np.random.randn(self.hidden_dim, 1) * 0.01
            self.b2 = np.zeros(1)
            self._initialized = True

    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def score(self, query_embedding: np.ndarray, doc_embedding: np.ndarray) -> float:
        input_dim = query_embedding.shape[-1]
        self._ensure_init(input_dim)
        x = np.concatenate([query_embedding, doc_embedding])
        h = self._relu(x @ self.w1 + self.b1)
        logit = (h @ self.w2 + self.b2).item()
        return float(1.0 / (1.0 + math.exp(-logit)))

    def rerank(self, query_embedding: np.ndarray, documents: List[Document], candidate_ids: List[int], top_k: int = 5) -> List[int]:
        scores = []
        for doc_id in candidate_ids:
            doc = documents[doc_id]
            if doc.embedding is None:
                continue
            score = self.score(query_embedding, doc.embedding)
            scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [doc_id for doc_id, _ in scores[:top_k]]


class HybridRAG:
    """Hybrid RAG pipeline combining dense, sparse, and reranking."""

    def __init__(self, documents: List[Document], reranker: Optional[CrossEncoderReranker] = None):
        self.documents = documents
        self.reranker = reranker or CrossEncoderReranker()
        self.doc_tokens = [_tokenize(doc.text) for doc in documents]

    def query(self, query_text: str, query_embedding: Optional[np.ndarray] = None, top_k: int = 5) -> List[Document]:
        dense_results = dense_retrieval(query_embedding, self.documents, top_k=top_k * 2) if query_embedding is not None else []
        sparse_results = bm25_score(query_text, [doc.text for doc in self.documents])
        fused = reciprocal_rank_fusion([dense_results, sparse_results])
        candidate_ids = [doc_id for doc_id, _ in fused[:top_k * 2]]
        if query_embedding is not None and candidate_ids:
            reranked_ids = self.reranker.rerank(query_embedding, self.documents, candidate_ids, top_k=top_k)
            return [self.documents[i] for i in reranked_ids]
        return [self.documents[i] for i in candidate_ids[:top_k]]
