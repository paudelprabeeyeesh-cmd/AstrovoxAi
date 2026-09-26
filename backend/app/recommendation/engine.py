"""Recommendation engine with collaborative and content-based filtering."""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    user_id: str
    preferences: Dict[str, float] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Recommendation:
    item_id: str
    score: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RecommendationEngine:
    def __init__(self) -> None:
        self._profiles: Dict[str, UserProfile] = {}
        self._item_features: Dict[str, Dict[str, float]] = {}
        self._interactions: List[Tuple[str, str, float]] = []

    def update_profile(self, user_id: str, item_id: str, rating: float = 1.0) -> None:
        profile = self._profiles.setdefault(user_id, UserProfile(user_id=user_id))
        profile.history.append(item_id)
        profile.preferences[item_id] = profile.preferences.get(item_id, 0.0) + rating
        self._interactions.append((user_id, item_id, rating))

    def content_based(self, user_id: str, top_k: int = 10) -> List[Recommendation]:
        profile = self._profiles.get(user_id)
        if not profile:
            return []
        scores: Dict[str, float] = defaultdict(float)
        for item_id, pref in profile.preferences.items():
            features = self._item_features.get(item_id, {})
            for other_item, other_features in self._item_features.items():
                if other_item in profile.history:
                    continue
                similarity = self._cosine_similarity(features, other_features)
                scores[other_item] += pref * similarity
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [Recommendation(item_id=item_id, score=score, source="content_based") for item_id, score in ranked]

    def collaborative(self, user_id: str, top_k: int = 10) -> List[Recommendation]:
        profile = self._profiles.get(user_id)
        if not profile:
            return []
        scores: Dict[str, float] = defaultdict(float)
        for other_user, other_profile in self._profiles.items():
            if other_user == user_id:
                continue
            common = set(profile.history) & set(other_profile.history)
            if not common:
                continue
            similarity = len(common) / math.sqrt(len(profile.history) * len(other_profile.history))
            for item_id in other_profile.history:
                if item_id not in profile.history:
                    scores[item_id] += similarity * other_profile.preferences.get(item_id, 0.0)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [Recommendation(item_id=item_id, score=score, source="collaborative") for item_id, score in ranked]

    def add_item_features(self, item_id: str, features: Dict[str, float]) -> None:
        self._item_features[item_id] = features

    def recommend(self, user_id: str, top_k: int = 10) -> List[Recommendation]:
        content = self.content_based(user_id, top_k)
        collab = self.collaborative(user_id, top_k)
        combined: Dict[str, Recommendation] = {}
        for rec in content + collab:
            if rec.item_id not in combined or combined[rec.item_id].score < rec.score:
                combined[rec.item_id] = rec
        return sorted(combined.values(), key=lambda r: r.score, reverse=True)[:top_k]

    @staticmethod
    def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
        keys = set(a) & set(b)
        if not keys:
            return 0.0
        dot = sum(a[k] * b[k] for k in keys)
        mag_a = math.sqrt(sum(a[k] ** 2 for k in keys))
        mag_b = math.sqrt(sum(b[k] ** 2 for k in keys))
        return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


recommendation_engine = RecommendationEngine()
