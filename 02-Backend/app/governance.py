"""Governance — security reviews, privacy, compliance, accessibility."""

import time
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Review:
    """A governance review."""
    id: str
    review_type: str
    status: str
    findings: list = None
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()
        if self.findings is None:
            self.findings = []


class GovernanceManager:
    """Manage governance."""

    def __init__(self):
        self._reviews: dict[str, Review] = {}
        self._policies: dict = {}

    def create_review(self, review_type: str) -> Review:
        """Create a review."""
        import secrets
        review = Review(
            id=secrets.token_hex(8),
            review_type=review_type,
            status="in_progress",
        )
        self._reviews[review.id] = review
        return review

    def add_finding(self, review_id: str, finding: str, severity: str):
        review = self._reviews.get(review_id)
        if review:
            review.findings.append({"text": finding, "severity": severity})

    def complete_review(self, review_id: str):
        review = self._reviews.get(review_id)
        if review:
            review.status = "completed"

    def add_policy(self, name: str, content: str):
        self._policies[name] = {"content": content, "created_at": time.time()}

    def get_reviews(self, status: str = None) -> list:
        reviews = list(self._reviews.values())
        if status:
            reviews = [r for r in reviews if r.status == status]
        return reviews


governance = GovernanceManager()
