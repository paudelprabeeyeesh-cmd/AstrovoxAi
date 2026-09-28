"""Hybrid retrieval combining BM25 lexical and vector semantic search."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from models.llm.retrieval.query import QueryExpander


@dataclass
class RetrievalDocument:
    doc_id: str
    text: str
    metadata: dict[str, Any]
    score: float = 0.0
    bm25_score: float = 0.0
    vector_score: float = 0.0
    rerank_score: float = 0.0


@dataclass
class RetrievalResult:
    query: str
    documents: list[RetrievalDocument]
    total_candidates: int = 0


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._corpus: list[list[str]] = []
        self._doc_lengths: list[int] = []
        self._avgdl: float = 0.0
        self._idf: dict[str, float] = {}
        self._term_freqs: list[dict[str, int]] = []

    def index_documents(self, documents: list[RetrievalDocument]) -> None:
        self._corpus = []
        self._doc_lengths = []
        self._term_freqs = []
        for doc in documents:
            tokens = doc.text.lower().split()
            self._corpus.append(tokens)
            self._doc_lengths.append(len(tokens))
            tf: dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self._term_freqs.append(tf)
        if self._doc_lengths:
            self._avgdl = sum(self._doc_lengths) / len(self._doc_lengths)
        else:
            self._avgdl = 0.0
        num_docs = len(self._corpus)
        all_terms: set[str] = set()
        for tf in self._term_freqs:
            all_terms.update(tf.keys())
        self._idf = {}
        for term in all_terms:
            df = sum(1 for tf in self._term_freqs if term in tf)
            self._idf[term] = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)

    def score(self, query: str, doc_idx: int) -> float:
        if doc_idx >= len(self._term_freqs) or not self._idf:
            return 0.0
        tokens = query.lower().split()
        tf = self._term_freqs[doc_idx]
        dl = self._doc_lengths[doc_idx]
        score = 0.0
        for term in tokens:
            if term not in tf or term not in self._idf:
                continue
            f = tf[term]
            idf = self._idf[term]
            num = f * (self.k1 + 1.0)
            denom = f + self.k1 * (1.0 - self.b + self.b * dl / (self._avgdl if self._avgdl > 0 else 1.0))
            score += idf * num / denom
        return score

    def search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        scores = [(i, self.score(query, i)) for i in range(len(self._corpus))]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class VectorIndex:
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self._vectors: list[list[float]] = []

    def add_documents(self, documents: list[RetrievalDocument], embed_fn) -> None:
        self._vectors = []
        for doc in documents:
            embedding = embed_fn(doc.text)
            self._vectors.append(list(embedding))

    def search(self, query: str, top_k: int = 10, embed_fn=None) -> list[tuple[int, float]]:
        if not self._vectors or embed_fn is None:
            return []
        query_vec = list(embed_fn(query))
        scores: list[tuple[int, float]] = []
        for i, vec in enumerate(self._vectors):
            sim = self._cosine_similarity(query_vec, vec)
            scores.append((i, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)


class FusionStrategy:
    @staticmethod
    def reciprocal_rank_fusion(
        bm25_results: list[tuple[int, float]],
        vector_results: list[tuple[int, float]],
        k: int = 60,
    ) -> list[tuple[int, float]]:
        scores: dict[int, float] = {}
        for rank, (doc_idx, _) in enumerate(bm25_results):
            scores[doc_idx] = scores.get(doc_idx, 0.0) + 1.0 / (k + rank + 1)
        for rank, (doc_idx, _) in enumerate(vector_results):
            scores[doc_idx] = scores.get(doc_idx, 0.0) + 1.0 / (k + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    @staticmethod
    def linear_fusion(
        bm25_results: list[tuple[int, float]],
        vector_results: list[tuple[int, float]],
        alpha: float = 0.5,
    ) -> list[tuple[int, float]]:
        bm25_max = max((s for _, s in bm25_results), default=1.0)
        vec_max = max((s for _, s in vector_results), default=1.0)
        scores: dict[int, float] = {}
        for doc_idx, s in bm25_results:
            scores[doc_idx] = scores.get(doc_idx, 0.0) + (s / bm25_max if bm25_max > 0 else 0.0) * alpha
        for doc_idx, s in vector_results:
            scores[doc_idx] = scores.get(doc_idx, 0.0) + (s / vec_max if vec_max > 0 else 0.0) * (1.0 - alpha)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    @staticmethod
    def score_fusion(
        bm25_results: list[tuple[int, float]],
        vector_results: list[tuple[int, float]],
        alpha: float = 0.5,
    ) -> list[tuple[int, float]]:
        scores: dict[int, float] = {}
        for doc_idx, s in bm25_results:
            scores[doc_idx] = scores.get(doc_idx, 0.0) + s * alpha
        for doc_idx, s in vector_results:
            scores[doc_idx] = scores.get(doc_idx, 0.0) + s * (1.0 - alpha)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class HybridRetriever:
    def __init__(
        self,
        embed_fn=None,
        fusion_strategy: str = "rrf",
        alpha: float = 0.5,
        k: int = 60,
        top_k: int = 10,
    ):
        self.bm25_index = BM25Index()
        self.vector_index = VectorIndex()
        self.embed_fn = embed_fn
        self.fusion_strategy = fusion_strategy
        self.alpha = alpha
        self.k = k
        self.top_k = top_k
        self._documents: list[RetrievalDocument] = []
        self.query_expander = QueryExpander()

    def index(self, documents: list[RetrievalDocument]) -> None:
        self._documents = documents
        self.bm25_index.index_documents(documents)
        if self.embed_fn is not None:
            self.vector_index.add_documents(documents, self.embed_fn)

    def retrieve(self, query: str, expand_query: bool = True) -> RetrievalResult:
        queries = self.query_expander.expand(query) if expand_query else [query]
        all_fused: dict[int, float] = {}
        for q in queries:
            bm25_results = self.bm25_index.search(q, self.top_k * 2)
            vector_results = self.vector_index.search(q, self.top_k * 2, self.embed_fn)
            if self.fusion_strategy == "rrf":
                fused = FusionStrategy.reciprocal_rank_fusion(bm25_results, vector_results, self.k)
            elif self.fusion_strategy == "linear":
                fused = FusionStrategy.linear_fusion(bm25_results, vector_results, self.alpha)
            else:
                fused = FusionStrategy.score_fusion(bm25_results, vector_results, self.alpha)
            for doc_idx, score in fused:
                all_fused[doc_idx] = all_fused.get(doc_idx, 0.0) + score
        ranked = sorted(all_fused.items(), key=lambda x: x[1], reverse=True)
        total_candidates = len(ranked)
        result_docs: list[RetrievalDocument] = []
        for doc_idx, score in ranked[: self.top_k]:
            doc = self._documents[doc_idx]
            result_docs.append(
                RetrievalDocument(
                    doc_id=doc.doc_id,
                    text=doc.text,
                    metadata=doc.metadata,
                    score=score,
                    bm25_score=doc.bm25_score,
                    vector_score=doc.vector_score,
                    rerank_score=doc.rerank_score,
                )
            )
        return RetrievalResult(query=query, documents=result_docs, total_candidates=total_candidates)
