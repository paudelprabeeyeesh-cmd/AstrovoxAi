"""Cross-encoder reranking for improved retrieval quality."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from models.llm.retrieval.hybrid import RetrievalDocument


@dataclass
class RerankResult:
    original: RetrievalDocument
    score: float
    rank: int


class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model: Any = None

    def _load_model(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder as _CrossEncoder
                self._model = _CrossEncoder(self.model_name)
            except ImportError:
                self._model = None

    def score(self, query: str, documents: list[RetrievalDocument]) -> list[float]:
        self._load_model()
        if self._model is not None:
            pairs = [[query, doc.text] for doc in documents]
            scores = self._model.predict(pairs)
            return list(scores)
        scores = []
        query_terms = set(query.lower().split())
        for doc in documents:
            doc_terms = set(doc.text.lower().split())
            overlap = len(query_terms & doc_terms)
            scores.append(float(overlap) / (len(query_terms) + 1e-6))
        return scores

    def rerank(self, query: str, documents: list[RetrievalDocument], top_k: int = 5) -> list[RerankResult]:
        scores = self.score(query, documents)
        scored = [(doc, score) for doc, score in zip(documents, scores)]
        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for rank, (doc, score) in enumerate(scored[:top_k]):
            results.append(RerankResult(original=doc, score=score, rank=rank))
        return results


class ScoreFusion:
    @staticmethod
    def fuse(
        retrieval_scores: list[tuple[int, float]],
        rerank_scores: list[tuple[int, float]],
        alpha: float = 0.7,
    ) -> list[tuple[int, float]]:
        max_retrieval = max((s for _, s in retrieval_scores), default=1.0)
        max_rerank = max((s for _, s in rerank_scores), default=1.0)
        scores: dict[int, float] = {}
        for doc_idx, s in retrieval_scores:
            norm = s / max_retrieval if max_retrieval > 0 else 0.0
            scores[doc_idx] = scores.get(doc_idx, 0.0) + norm * alpha
        for doc_idx, s in rerank_scores:
            norm = s / max_rerank if max_rerank > 0 else 0.0
            scores[doc_idx] = scores.get(doc_idx, 0.0) + norm * (1.0 - alpha)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    @staticmethod
    def weighted_sum(
        retrieval_scores: list[tuple[int, float]],
        rerank_scores: list[tuple[int, float]],
        alpha: float = 0.5,
    ) -> list[tuple[int, float]]:
        ret_map = {idx: s for idx, s in retrieval_scores}
        rerank_map = {idx: s for idx, s in rerank_scores}
        all_indices = set(ret_map.keys()) | set(rerank_map.keys())
        scores = []
        for idx in all_indices:
            r = ret_map.get(idx, 0.0)
            rr = rerank_map.get(idx, 0.0)
            scores.append((idx, alpha * r + (1.0 - alpha) * rr))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


class TopKSelector:
    def __init__(self, k: int = 10, threshold: float = 0.0):
        self.k = k
        self.threshold = threshold

    def select(self, documents: list[RetrievalDocument]) -> list[RetrievalDocument]:
        filtered = [doc for doc in documents if doc.score >= self.threshold]
        filtered.sort(key=lambda doc: doc.score, reverse=True)
        return filtered[: self.k]
