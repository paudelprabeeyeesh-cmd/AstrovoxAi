"""Rating and review system for marketplace."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Rating:
    rating_id: str
    listing_id: str
    user_id: str
    score: float
    review: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RatingManager:
    def __init__(self) -> None:
        self._ratings: Dict[str, Rating] = {}

    def add_rating(self, listing_id: str, user_id: str, score: float, review: str = "") -> Rating:
        rating_id = f"{listing_id}:{user_id}"
        rating = Rating(rating_id=rating_id, listing_id=listing_id, user_id=user_id, score=score, review=review)
        self._ratings[rating_id] = rating
        return rating

    def get_ratings(self, listing_id: str) -> List[Rating]:
        return [r for r in self._ratings.values() if r.listing_id == listing_id]

    def average_score(self, listing_id: str) -> float:
        ratings = self.get_ratings(listing_id)
        return sum(r.score for r in ratings) / len(ratings) if ratings else 0.0


rating_manager = RatingManager()
