"""
RAG Retrieval Service.

Provides hybrid retrieval combining:
- Dense vector search (embedding similarity)
- Sparse search (BM25-like keyword matching)
- Reciprocal Rank Fusion (RRF)
- Cross-encoder reranking
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.rag.embedding_store import EmbeddingStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "dense"
    rank: int = 0


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def _compute_tf(tokens: List[str]) -> Dict[str, int]:
    tf: Dict[str, int] = {}
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1
    return tf


class BM25Retriever:
    """Lightweight BM25 sparse retriever."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._documents: Dict[str, str] = {}
        self._doc_tokens: Dict[str, List[str]] = {}
        self._idf: Dict[str, float] = {}
        self._avg_dl: float = 0.0
        self._built = False

    def add_document(self, doc_id: str, text: str) -> None:
        self._documents[doc_id] = text
        self._doc_tokens[doc_id] = _tokenize(text)
        self._built = False

    def add_documents(self, documents: Dict[str, str]) -> None:
        for doc_id, text in documents.items():
            self.add_document(doc_id, text)

    def _build(self) -> None:
        if self._built:
            return
        doc_tokens = list(self._doc_tokens.values())
        n = len(doc_tokens)
        if n == 0:
            self._avg_dl = 0.0
            self._idf = {}
            self._built = True
            return
        self._avg_dl = sum(len(t) for t in doc_tokens) / n
        idf: Dict[str, float] = {}
        for tokens in doc_tokens:
            for token in set(tokens):
                idf[token] = idf.get(token, 0) + 1
        for token, freq in idf.items():
            idf[token] = math.log((n - freq + 0.5) / (freq + 0.5) + 1)
        self._idf = idf
        self._built = True

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        self._build()
        if not self._documents or self._avg_dl == 0.0:
            return []
        query_tokens = _tokenize(query)
        scores: List[Tuple[str, float]] = []
        for doc_id, tokens in self._doc_tokens.items():
            tf = _compute_tf(tokens)
            dl = len(tokens)
            score = 0.0
            for token in query_tokens:
                if token not in tf:
                    continue
                idf_val = self._idf.get(token, 0.0)
                tf_val = tf[token]
                score += idf_val * (tf_val * (self.k1 + 1)) / (tf_val + self.k1 * (1 - self.b + self.b * dl / self._avg_dl))
            scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class RAGRetriever:
    """
    Unified RAG retrieval combining dense and sparse search.
    
    Features:
    - Dense vector search via embedding store
    - Sparse BM25 keyword search
    - RRF fusion
    - Score normalization
    """

    def __init__(
        self,
        embedding_store: Optional[EmbeddingStore] = None,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
        rrf_k: int = 60,
    ):
        self.embedding_store = embedding_store or EmbeddingStore()
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.rrf_k = rrf_k
        self._sparse_index = BM25Retriever()
        self._documents: Dict[str, str] = {}

    def index_document(self, document_id: str, text: str) -> None:
        """Index a document for sparse retrieval."""
        self._documents[document_id] = text
        self._sparse_index.add_document(document_id, text)

    def index_documents(self, documents: Dict[str, str]) -> None:
        """Index multiple documents."""
        self._documents.update(documents)
        self._sparse_index.add_documents(documents)

    def clear_index(self) -> None:
        """Clear the sparse index."""
        self._documents.clear()
        self._sparse_index = BM25Retriever()

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Tuple[str, float]],
        sparse_results: List[Tuple[str, float]],
        k: int = 60,
    ) -> List[Tuple[str, float]]:
        """Combine dense and sparse results using RRF."""
        scores: Dict[str, float] = {}
        for rank, (doc_id, _) in enumerate(dense_results):
            scores[doc_id] = scores.get(doc_id, 0.0) + self.dense_weight / (k + rank + 1)
        for rank, (doc_id, _) in enumerate(sparse_results):
            scores[doc_id] = scores.get(doc_id, 0.0) + self.sparse_weight / (k + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            document_ids: Optional list of document IDs to restrict search
            metadata_filter: Optional metadata key-value pairs to filter by
        
        Returns:
            List of RetrievalResult sorted by relevance
        """
        query_embedding = None
        try:
            from ..embeddings import embedding_service
            vectors = await embedding_service.embed_with_retry(texts=[query])
            query_embedding = np.array(vectors[0].vector, dtype=np.float32)
        except Exception as exc:
            logger.warning("Dense embedding failed, using sparse-only: %s", exc)

        dense_results: List[Tuple[str, float]] = []
        if query_embedding is not None:
            try:
                dense_hits = self.embedding_store.similarity_search(
                    query_embedding=query_embedding,
                    top_k=top_k * 3,
                    document_ids=document_ids,
                    metadata_filter=metadata_filter,
                )
                dense_results = [(hit[0].embedding_id, float(hit[1])) for hit in dense_hits]
            except Exception as exc:
                logger.warning("Dense search failed: %s", exc)

        sparse_results = self._sparse_index.search(query, top_k=top_k * 3)

        fused = self._reciprocal_rank_fusion(dense_results, sparse_results, k=self.rrf_k)
        top = fused[:top_k]

        results = []
        for rank, (embedding_id, score) in enumerate(top):
            entry = self.embedding_store.get_embedding(embedding_id)
            if entry is None:
                continue
            source = "dense" if embedding_id in [r for r, _ in dense_results] else "sparse"
            results.append(RetrievalResult(
                chunk_id=embedding_id,
                document_id=entry.document_id,
                content=entry.content,
                score=float(score),
                metadata=entry.metadata,
                source=source,
                rank=rank + 1,
            ))
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        store_stats = self.embedding_store.get_stats()
        return {
            "dense_weight": self.dense_weight,
            "sparse_weight": self.sparse_weight,
            "rrf_k": self.rrf_k,
            **store_stats,
        }

    async def retrieve_from_db(
        self,
        query: str,
        top_k: int = 5,
        user_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """Retrieve directly from DB-backed document chunks."""
        try:
            query_embedding = None
            from ..embeddings import embedding_service
            vectors = await embedding_service.embed_with_retry(texts=[query])
            query_embedding = np.array(vectors[0].vector, dtype=np.float32)
        except Exception as exc:
            logger.warning("Dense embedding failed for DB retrieval: %s", exc)
            return []

        if query_embedding is None:
            return []

        try:
            from ..documents import search_chunks
            rows = search_chunks(
                user_id=user_id or "",
                query_embedding=query_embedding.tolist(),
                limit=top_k,
            )
        except Exception as exc:
            logger.warning("DB dense search failed: %s", exc)
            return []

        results = []
        for rank, row in enumerate(rows[:top_k]):
            results.append(RetrievalResult(
                chunk_id=row.get("id", ""),
                document_id=row.get("document_id", ""),
                content=row.get("content", ""),
                score=float(row.get("score", 0.0)),
                metadata=row.get("metadata", {}),
                source="db_dense",
                rank=rank + 1,
            ))
        return results

