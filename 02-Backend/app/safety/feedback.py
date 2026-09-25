"""Human feedback collection flow."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FeedbackEntry:
    id: str
    user_id: Optional[str]
    interaction_id: str
    rating: int
    comment: Optional[str]
    categories: list[str] = field(default_factory=list)
    submitted_at: float = field(default_factory=time.time)
    reviewed: bool = False
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[float] = None


class HumanFeedbackCollector:
    """Collect and manage human feedback on AI outputs."""

    def __init__(self):
        self._entries: dict[str, FeedbackEntry] = {}
        self._pending: list[str] = []

    def submit_feedback(
        self,
        interaction_id: str,
        rating: int,
        user_id: Optional[str] = None,
        comment: Optional[str] = None,
        categories: Optional[list[str]] = None,
    ) -> FeedbackEntry:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        entry = FeedbackEntry(
            id=str(uuid.uuid4())[:8],
            user_id=user_id,
            interaction_id=interaction_id,
            rating=rating,
            comment=comment,
            categories=categories or [],
        )
        self._entries[entry.id] = entry
        self._pending.append(entry.id)
        logger.info("Feedback collected: %s rating=%d", entry.id, rating)
        return entry

    def get_pending(self, limit: int = 50) -> list[FeedbackEntry]:
        pending = [self._entries[eid] for eid in self._pending if eid in self._entries]
        return pending[:limit]

    def review_feedback(self, entry_id: str, reviewer_id: str, action: str = "acknowledge") -> bool:
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        entry.reviewed = True
        entry.reviewer_id = reviewer_id
        entry.reviewed_at = time.time()
        if entry_id in self._pending:
            self._pending.remove(entry_id)
        logger.info("Feedback reviewed: %s by %s", entry_id, reviewer_id)
        return True

    def get_feedback_for_interaction(self, interaction_id: str) -> list[FeedbackEntry]:
        return [e for e in self._entries.values() if e.interaction_id == interaction_id]

    def get_feedback_summary(self) -> dict:
        entries = list(self._entries.values())
        if not entries:
            return {"count": 0, "average_rating": 0.0, "pending": 0}
        ratings = [e.rating for e in entries]
        return {
            "count": len(entries),
            "average_rating": round(sum(ratings) / len(ratings), 2),
            "pending": len(self._pending),
            "rating_distribution": {
                str(i): sum(1 for r in ratings if r == i) for i in range(1, 6)
            },
            "recent": [
                {
                    "id": e.id,
                    "rating": e.rating,
                    "comment": e.comment,
                    "submitted_at": datetime.fromtimestamp(e.submitted_at).isoformat(),
                }
                for e in entries[-10:]
            ],
        }

    def get_low_rated(self, threshold: int = 2) -> list[FeedbackEntry]:
        return [e for e in self._entries.values() if e.rating <= threshold]

    def get_category_feedback(self, category: str) -> list[FeedbackEntry]:
        return [e for e in self._entries.values() if category in e.categories]


human_feedback_collector = HumanFeedbackCollector()
