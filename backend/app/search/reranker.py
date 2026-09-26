"""Result reranker for search and retrieval."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RankedResult:
    result_id: str
    score: float
    original_score: float
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    rank: int = 0


class Reranker:
    def __init__(self) -> None:
        self._models: Dict[str, Any] = {}

    def register_model(self, name: str, model: Any) -> None:
        self._models[name] = model
        logger.info("Registered reranker model %s", name)

    def rank(self, results: List[Dict[str, Any]], query: str, model_name: str = "default", top_k: int = 10) -> List[RankedResult]:
        model = self._models.get(model_name)
        ranked = []
        for idx, result in enumerate(results):
            content = result.get("content", "")
            original_score = result.get("score", 0.0)
            if model:
                try:
                    rerank_score = float(model(query, content))
                except Exception:
                    rerank_score = original_score
            else:
                rerank_score = original_score
            ranked.append(RankedResult(
                result_id=result.get("id", str(idx)),
                score=rerank_score,
                original_score=original_score,
                content=content,
                metadata=result.get("metadata", {}),
            ))
        ranked.sort(key=lambda r: r.score, reverse=True)
        for idx, r in enumerate(ranked[:top_k]):
            r.rank = idx + 1
        return ranked[:top_k]

    def reciprocal_rank_fusion(self, result_lists: List[List[Dict[str, Any]]], k: int = 60) -> List[RankedResult]:
        scores: Dict[str, float] = {}
        contents: Dict[str, str] = {}
        for results in result_lists:
            for rank, result in enumerate(results, start=1):
                rid = result.get("id", str(rank))
                scores[rid] = scores.get(rid, 0.0) + 1.0 / (k + rank)
                contents[rid] = result.get("content", "")
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [
            RankedResult(result_id=rid, score=score, original_score=score, content=contents.get(rid, ""), rank=idx + 1)
            for idx, (rid, score) in enumerate(ranked)
        ]


reranker = Reranker()
