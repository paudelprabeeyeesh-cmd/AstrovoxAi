"""Memory ranking and retrieval scoring."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RankingFactor(Enum):
    RECENCY = "recency"
    FREQUENCY = "frequency"
    IMPORTANCE = "importance"
    SIMILARITY = "similarity"
    CONTEXT_RELEVANCE = "context_relevance"


@dataclass
class MemoryScore:
    memory_id: str
    base_score: float
    factors: Dict[RankingFactor, float] = field(default_factory=dict)
    final_score: float = 0.0
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryRanker:
    _weights: Dict[RankingFactor, float] = {
        RankingFactor.RECENCY: 0.25,
        RankingFactor.FREQUENCY: 0.15,
        RankingFactor.IMPORTANCE: 0.25,
        RankingFactor.SIMILARITY: 0.25,
        RankingFactor.CONTEXT_RELEVANCE: 0.10,
    }

    @classmethod
    def rank(cls, memories: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> List[MemoryScore]:
        scores = []
        for memory in memories:
            factors = cls._compute_factors(memory, context)
            final_score = sum(cls._weights.get(factor, 0) * score for factor, score in factors.items())
            score = MemoryScore(
                memory_id=memory.get("id", ""),
                base_score=final_score,
                factors=factors,
                final_score=final_score,
            )
            scores.append(score)
        scores.sort(key=lambda s: s.final_score, reverse=True)
        return scores

    @classmethod
    def _compute_factors(cls, memory: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[RankingFactor, float]:
        factors = {}
        created_at = memory.get("created_at", datetime.now(timezone.utc))
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
        factors[RankingFactor.RECENCY] = max(0, 1 - (age_hours / 168))
        factors[RankingFactor.FREQUENCY] = min(1.0, memory.get("access_count", 0) / 100)
        factors[RankingFactor.IMPORTANCE] = memory.get("importance", 0.5)
        factors[RankingFactor.SIMILARITY] = 0.5
        factors[RankingFactor.CONTEXT_RELEVANCE] = 0.5
        return factors
