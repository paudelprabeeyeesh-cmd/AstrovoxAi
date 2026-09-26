"""Access review for governance."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReviewFinding:
    finding_id: str
    user_id: str
    resource: str
    risk_level: str
    recommendation: str


@dataclass
class AccessReview:
    review_id: str
    reviewer_id: str
    findings: List[ReviewFinding] = field(default_factory=list)
    status: str = "in_progress"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AccessReviewManager:
    def __init__(self) -> None:
        self._reviews: Dict[str, AccessReview] = {}

    def start_review(self, reviewer_id: str) -> AccessReview:
        review_id = uuid.uuid4().hex
        review = AccessReview(review_id=review_id, reviewer_id=reviewer_id)
        self._reviews[review_id] = review
        return review

    def add_finding(self, review_id: str, finding: ReviewFinding) -> None:
        review = self._reviews.get(review_id)
        if review:
            review.findings.append(finding)


access_review_manager = AccessReviewManager()
