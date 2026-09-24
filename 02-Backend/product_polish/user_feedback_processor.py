"""
user_feedback_processor - product_polish

Collect, analyze, and report on user feedback.
"""

from __future__ import annotations

import copy
import logging
import re
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FeedbackItem:
    id: str
    user_id: str
    source: str
    content: str
    rating: Optional[int] = None
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source": self.source,
            "content": self.content,
            "rating": self.rating,
            "category": self.category,
            "tags": self.tags,
            "meta": self.meta,
            "created_at": self.created_at,
        }


class UserFeedbackProcessor:
    def __init__(self):
        self._feedback: Dict[str, FeedbackItem] = {}
        self._lock = threading.Lock()

    def submit_feedback(
        self,
        user_id: str,
        source: str,
        content: str,
        rating: Optional[int] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> FeedbackItem:
        import uuid
        feedback_id = str(uuid.uuid4())
        if rating is not None and not 1 <= rating <= 5:
            raise ValueError("rating must be between 1 and 5")
        item = FeedbackItem(
            id=feedback_id,
            user_id=user_id,
            source=source,
            content=content,
            rating=rating,
            category=category,
            tags=tags or [],
            meta=meta or {},
        )
        with self._lock:
            self._feedback[feedback_id] = item
        logger.info("Submitted feedback %s from %s", feedback_id, user_id)
        return item

    def get_feedback(self, feedback_id: str) -> Optional[FeedbackItem]:
        with self._lock:
            return self._feedback.get(feedback_id)

    def list_feedback(self, category: Optional[str] = None, min_rating: Optional[int] = None) -> List[FeedbackItem]:
        with self._lock:
            items = list(self._feedback.values())
        if category is not None:
            items = [f for f in items if f.category == category]
        if min_rating is not None:
            items = [f for f in items if f.rating is not None and f.rating >= min_rating]
        return sorted(items, key=lambda f: f.created_at, reverse=True)

    def analyze(self) -> Dict[str, Any]:
        with self._lock:
            items = list(self._feedback.values())
        total = len(items)
        ratings = [f.rating for f in items if f.rating is not None]
        category_counter = Counter(f.category for f in items)
        source_counter = Counter(f.source for f in items)
        tag_counter = Counter(tag for f in items for tag in f.tags)
        analysis = {
            "total_feedback": total,
            "rating_distribution": dict(Counter(ratings)),
            "average_rating": sum(ratings) / len(ratings) if ratings else None,
            "by_category": dict(category_counter),
            "by_source": dict(source_counter),
            "top_tags": tag_counter.most_common(10),
            "negative_keywords": self._extract_keywords(items, negative=True),
            "positive_keywords": self._extract_keywords(items, negative=False),
        }
        return analysis

    def _extract_keywords(self, items: List[FeedbackItem], negative: bool) -> List[str]:
        negative_words = {"bad", "slow", "bug", "broken", "crash", "error", "issue", "problem", "worst"}
        positive_words = {"great", "fast", "good", "awesome", "love", "best", "excellent", "helpful"}
        target_words = negative_words if negative else positive_words
        found: List[str] = []
        for item in items:
            tokens = set(re.findall(r"[a-z]+", item.content.lower()))
            found.extend(target_words.intersection(tokens))
        counter = Counter(found)
        return [word for word, _ in counter.most_common(5)]

    def search(self, query: str) -> List[FeedbackItem]:
        with self._lock:
            items = list(self._feedback.values())
        terms = [t.lower() for t in re.findall(r"[a-z]+", query.lower())]
        scored = []
        for item in items:
            text = item.content.lower()
            score = sum(text.count(term) for term in terms)
            if score > 0:
                scored.append((score, item))
        return [item for _, item in sorted(scored, reverse=True)]
