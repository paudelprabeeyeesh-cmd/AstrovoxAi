"""Adaptive retrieval depth and dynamic routing by quality/cost."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    chunk_ids: list[str]
    scores: list[float]
    depth: int
    stopped_early: bool


class AdaptiveRetrieval:
    def retrieve(self, query: str, initial_depth: int = 3, max_depth: int = 8, threshold: float = 0.78) -> RetrievalResult:
        depth = initial_depth
        chunk_ids: list[str] = []
        scores: list[float] = []
        stopped_early = False
        while depth <= max_depth:
            ids, sc = self._search(query, depth)
            chunk_ids.extend(ids)
            scores.extend(sc)
            if sc and max(sc) >= threshold:
                stopped_early = True
                break
            depth += 1
        return RetrievalResult(chunk_ids=chunk_ids, scores=scores, depth=depth, stopped_early=stopped_early)

    def _search(self, query: str, depth: int) -> tuple[list[str], list[float]]:
        try:
            from app.rag_engine import RAGEngine
            engine = RAGEngine()
            results = engine.search(query, top_k=depth)
            return [r.get("chunk_id", r.get("id", "")) for r in results], [float(r.get("score", 0.0)) for r in results]
        except Exception as exc:
            logger.error("Adaptive retrieval failed: %s", exc)
            return [], []


@dataclass
class ModelOption:
    provider: str
    model: str
    cost_per_1k_tokens: float
    quality_score: float


class DynamicModelRouter:
    def __init__(self, budget_per_request: float = 0.05, min_quality: float = 0.8) -> None:
        self.budget_per_request = budget_per_request
        self.min_quality = min_quality
        self.options = [
            ModelOption("openai", "gpt-4o", cost_per_1k_tokens=0.03, quality_score=0.95),
            ModelOption("anthropic", "claude-3-5-sonnet", cost_per_1k_tokens=0.025, quality_score=0.94),
            ModelOption("google", "gemini-1.5-pro", cost_per_1k_tokens=0.012, quality_score=0.88),
            ModelOption("groq", "llama-3.3-70b", cost_per_1k_tokens=0.002, quality_score=0.78),
            ModelOption("ollama", "llama-3.3-70b", cost_per_1k_tokens=0.0, quality_score=0.72),
        ]

    def select(self, estimated_tokens: int = 1000) -> ModelOption:
        eligible = [opt for opt in self.options if opt.quality_score >= self.min_quality]
        if not eligible:
            eligible = list(self.options)
        eligible.sort(key=lambda opt: opt.cost_per_1k_tokens)
        return eligible[0]
