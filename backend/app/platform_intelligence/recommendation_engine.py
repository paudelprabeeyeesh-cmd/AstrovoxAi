"""Recommendation engine for platform suggestions."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    recommendation_id: str
    user_id: str
    item_id: str
    score: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RecommendationEngine:
    def __init__(self) -> None:
        self._recommendations: List[Recommendation] = []

    def recommend(self, user_id: str, candidates: List[str], scores: List[float]) -> List[Recommendation]:
        results = []
        for item_id, score in zip(candidates, scores):
            rec = Recommendation(
                recommendation_id=item_id,
                user_id=user_id,
                item_id=item_id,
                score=score,
                reason="content_similarity",
            )
            results.append(rec)
            self._recommendations.append(rec)
        return results

    def get_recommendations(self, user_id: str) -> List[Recommendation]:
        return [r for r in self._recommendations if r.user_id == user_id]


recommendation_engine = RecommendationEngine()
