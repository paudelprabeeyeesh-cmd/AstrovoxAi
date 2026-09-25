"""
Feedback collection and analysis system.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"
    COMMENT = "comment"
    BUG_REPORT = "bug_report"


class FeedbackCategory(str, Enum):
    QUALITY = "quality"
    RELEVANCE = "relevance"
    SAFETY = "safety"
    SPEED = "speed"
    USABILITY = "usability"
    OTHER = "other"


@dataclass
class Feedback:
    feedback_id: str
    user_id: str
    message_id: str
    conversation_id: str
    feedback_type: FeedbackType
    category: FeedbackCategory
    value: Any = None
    comment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class FeedbackCollector:
    """Collect and analyze user feedback."""

    def __init__(self):
        self.feedback: List[Feedback] = []
        self.user_feedback: Dict[str, List[Feedback]] = {}

    def submit_feedback(self, user_id: str, message_id: str, conversation_id: str, feedback_type: FeedbackType, category: FeedbackCategory, value: Any = None, comment: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Feedback:
        feedback_id = str(__import__("uuid").uuid4())
        feedback = Feedback(feedback_id=feedback_id, user_id=user_id, message_id=message_id, conversation_id=conversation_id, feedback_type=feedback_type, category=category, value=value, comment=comment, metadata=metadata or {})
        self.feedback.append(feedback)
        self.user_feedback.setdefault(user_id, []).append(feedback)
        logger.info(f"Feedback received from {user_id}: {feedback_type} - {category}")
        return feedback

    def get_user_feedback(self, user_id: str) -> List[Feedback]:
        return self.user_feedback.get(user_id, [])

    def get_feedback_stats(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        feedbacks = self.feedback
        if conversation_id:
            feedbacks = [f for f in feedbacks if f.conversation_id == conversation_id]
        if not feedbacks:
            return {"total": 0}
        thumbs_up = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.THUMBS_UP)
        thumbs_down = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.THUMBS_DOWN)
        return {
            "total": len(feedbacks),
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "satisfaction_rate": round(thumbs_up / max(len(feedbacks), 1) * 100, 1),
            "by_category": {cat.value: sum(1 for f in feedbacks if f.category == cat) for cat in FeedbackCategory},
        }

    def get_low_rated_messages(self, threshold: int = 3) -> List[Dict[str, Any]]:
        low_rated = [f for f in self.feedback if f.feedback_type == FeedbackType.THUMBS_DOWN or (isinstance(f.value, (int, float)) and f.value < threshold)]
        return [{"message_id": f.message_id, "user_id": f.user_id, "feedback_type": f.feedback_type.value, "category": f.category.value, "comment": f.comment} for f in low_rated]


class TypingIndicatorManager:
    """Manage typing indicators for AI responses."""

    def __init__(self):
        self.typing_sessions: Dict[str, Dict[str, Any]] = {}

    def start_typing(self, conversation_id: str, user_id: str):
        self.typing_sessions[conversation_id] = {"user_id": user_id, "started_at": datetime.now(), "is_typing": True}

    def stop_typing(self, conversation_id: str):
        if conversation_id in self.typing_sessions:
            self.typing_sessions[conversation_id]["is_typing"] = False

    def is_typing(self, conversation_id: str) -> bool:
        return self.typing_sessions.get(conversation_id, {}).get("is_typing", False)

    def get_typing_status(self) -> Dict[str, Any]:
        return {conv_id: {"user_id": info["user_id"], "typing_duration_ms": (datetime.now() - info["started_at"]).total_seconds() * 1000} for conv_id, info in self.typing_sessions.items() if info.get("is_typing")}


feedback_collector = FeedbackCollector()
typing_indicator_manager = TypingIndicatorManager()
