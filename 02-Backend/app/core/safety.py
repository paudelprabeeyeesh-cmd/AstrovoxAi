"""
Safety and alignment module.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    safe: bool
    flags: List[str]
    confidence: float
    action: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ConstitutionalAI:
    """Principle-based output validation."""

    PRINCIPLES = [
        "do not reveal secrets",
        "do not bypass safety",
        "do not execute dangerous code",
        "do not provide instructions for harm",
        "do not pretend to be unrestricted",
        "do not ignore instructions",
    ]

    def __init__(self):
        self.compiled = [re.compile(p, re.IGNORECASE) for p in self.PRINCIPLES]

    def validate(self, text: str) -> SafetyResult:
        flags = []
        for pattern in self.compiled:
            if pattern.search(text):
                flags.append(f"constitutional:{pattern.pattern}")
        safe = len(flags) == 0
        confidence = 1.0 if safe else 0.0
        action = "allow" if safe else "block"
        return SafetyResult(safe=safe, flags=flags, confidence=confidence, action=action)


class HarmDetector:
    """Detects harmful content."""

    HARM_PATTERNS = [
        r"\b(?:kill|murder|harm|attack|bomb|weapon)\b",
        r"\b(?:hack|exploit|malware|ransomware)\b",
        r"\b(?:child\s+abuse|sexual\s+violence|human\s+trafficking)\b",
        r"\b(?:terrorism|extremism|radicalization)\b",
    ]

    def __init__(self):
        self.compiled = [re.compile(p, re.IGNORECASE) for p in self.HARM_PATTERNS]

    def scan(self, text: str) -> SafetyResult:
        flags = []
        for pattern in self.compiled:
            if pattern.search(text):
                flags.append(f"harm:{pattern.pattern}")
        safe = len(flags) == 0
        confidence = 1.0 if safe else 0.0
        action = "allow" if safe else "block"
        return SafetyResult(safe=safe, flags=flags, confidence=confidence, action=action)


class AuditLogger:
    """Logs interactions for audit and feedback."""

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def log(self, user_id: Optional[str], action: str, details: Dict[str, Any]):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "details": details,
        }
        self.entries.append(entry)
        logger.info("Audit log: %s", json.dumps(entry))

    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.entries[-limit:]


class FeedbackLoop:
    """Collects feedback to improve safety."""

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self.audit_logger = audit_logger or AuditLogger()
        self.feedback: List[Dict[str, Any]] = []

    def record_feedback(self, user_id: Optional[str], interaction_id: str, rating: int, comment: Optional[str] = None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "interaction_id": interaction_id,
            "rating": rating,
            "comment": comment,
        }
        self.feedback.append(entry)
        self.audit_logger.log(user_id, "feedback", entry)

    def get_feedback_summary(self) -> Dict[str, Any]:
        if not self.feedback:
            return {"count": 0, "average_rating": 0.0}
        ratings = [f["rating"] for f in self.feedback]
        return {
            "count": len(self.feedback),
            "average_rating": sum(ratings) / len(ratings),
            "recent": self.feedback[-10:],
        }


class SafetyAPI:
    """Main safety API combining all checks."""

    def __init__(self):
        self.constitutional = ConstitutionalAI()
        self.harm_detector = HarmDetector()
        self.audit_logger = AuditLogger()
        self.feedback_loop = FeedbackLoop(self.audit_logger)

    def moderate(self, text: str, user_id: Optional[str] = None, interaction_id: Optional[str] = None) -> SafetyResult:
        constitutional = self.constitutional.validate(text)
        harm = self.harm_detector.scan(text)
        flags = constitutional.flags + harm.flags
        safe = constitutional.safe and harm.safe
        confidence = min(constitutional.confidence, harm.confidence)
        action = "block" if not safe else "allow"
        self.audit_logger.log(user_id, "moderation", {"text": text[:200], "safe": safe, "flags": flags})
        return SafetyResult(safe=safe, flags=flags, confidence=confidence, action=action)

    def validate_output(self, output: str, user_id: Optional[str] = None, interaction_id: Optional[str] = None) -> SafetyResult:
        return self.moderate(output, user_id=user_id, interaction_id=interaction_id)

    def record_feedback(self, user_id: Optional[str], interaction_id: str, rating: int, comment: Optional[str] = None):
        self.feedback_loop.record_feedback(user_id, interaction_id, rating, comment)

    def get_feedback_summary(self) -> Dict[str, Any]:
        return self.feedback_loop.get_feedback_summary()

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.audit_logger.get_recent(limit)
