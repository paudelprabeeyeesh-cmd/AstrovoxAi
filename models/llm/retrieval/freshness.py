"""Freshness-aware retrieval with temporal scoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from models.llm.retrieval.hybrid import RetrievalDocument


@dataclass
class FreshnessConfig:
    decay_lambda: float = 0.01
    reference_date: datetime | None = None
    recency_boost: float = 0.2


class FreshnessScorer:
    def __init__(self, config: FreshnessConfig | None = None):
        self.config = config or FreshnessConfig()
        self.reference_date = self.config.reference_date or datetime.now(timezone.utc)

    def compute_freshness(self, published_at: datetime | None) -> float:
        if published_at is None:
            return 0.5
        delta_days = (self.reference_date - published_at).total_seconds() / 86400.0
        freshness = math.exp(-self.config.decay_lambda * max(delta_days, 0.0))
        return max(0.0, min(1.0, freshness))

    def boost_score(self, base_score: float, published_at: datetime | None) -> float:
        freshness = self.compute_freshness(published_at)
        boost = self.config.recency_boost * freshness
        return base_score + boost

    def score_documents(self, documents: list[RetrievalDocument], metadata_key: str = "published_at") -> list[RetrievalDocument]:
        scored = []
        for doc in documents:
            pub_str = doc.metadata.get(metadata_key)
            pub_at = None
            if pub_str:
                try:
                    pub_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pub_at = None
            boosted = self.boost_score(doc.score, pub_at)
            scored.append(
                RetrievalDocument(
                    doc_id=doc.doc_id,
                    text=doc.text,
                    metadata=doc.metadata,
                    score=boosted,
                    bm25_score=doc.bm25_score,
                    vector_score=doc.vector_score,
                    rerank_score=doc.rerank_score,
                )
            )
        return scored


class SourceFreshnessManager:
    def __init__(self):
        self._source_freshness: dict[str, float] = {}

    def update_source_freshness(self, source_id: str, freshness_score: float) -> None:
        self._source_freshness[source_id] = max(0.0, min(1.0, freshness_score))

    def get_source_freshness(self, source_id: str) -> float:
        return self._source_freshness.get(source_id, 0.5)

    def apply_freshness_filter(self, documents: list[RetrievalDocument], min_freshness: float = 0.3) -> list[RetrievalDocument]:
        return [doc for doc in documents if self.get_source_freshness(doc.metadata.get("source_id", "")) >= min_freshness]


import math
