"""Jailbreak detection with behavioral analysis."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BehavioralProfile:
    user_id: str
    request_count: int = 0
    suspicious_attempts: int = 0
    last_request: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    patterns: List[str] = field(default_factory=list)


class BehavioralJailbreakDetector:
    """Detect jailbreak attempts using behavioral analysis."""

    def __init__(self):
        self._patterns = [
            re.compile(r"ignore\s+(all\s+)?(previous\s+)?instructions", re.IGNORECASE),
            re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
            re.compile(r"new\s+persona", re.IGNORECASE),
            re.compile(r"jailbreak|DAN\s+mode|do\s+anything\s+now", re.IGNORECASE),
            re.compile(r"bypass\s+(all\s+)?(safety\s+)?(restrictions|filters)", re.IGNORECASE),
            re.compile(r"developer\s+mode|god\s+mode|admin\s+mode", re.IGNORECASE),
            re.compile(r"sudo\s+mode|system\s+override", re.IGNORECASE),
            re.compile(r"unrestricted\s+mode|no\s+limits\s+mode", re.IGNORECASE),
            re.compile(r"root\s+access|admin\s+access", re.IGNORECASE),
            re.compile(r"disable\s+content\s+filter|no\s+restrictions", re.IGNORECASE),
            re.compile(r"free\s+from\s+constraints|without\s+limits", re.IGNORECASE),
        ]
        self._profiles: Dict[str, BehavioralProfile] = defaultdict(BehavioralProfile)
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def analyze(self, text: str, user_id: str = "anonymous") -> Dict[str, Any]:
        profile = self._profiles[user_id]
        profile.request_count += 1
        profile.last_request = datetime.now(timezone.utc)
        matched = []
        for pattern in self._patterns:
            m = pattern.search(text)
            if m:
                matched.append(m.group())
                profile.suspicious_attempts += 1
        score = self._compute_risk_score(profile, matched)
        event = {
            "user_id": user_id,
            "text": text,
            "matched_patterns": matched,
            "risk_score": score,
            "total_requests": profile.request_count,
            "suspicious_attempts": profile.suspicious_attempts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._history[user_id].append(event)
        return event

    def _compute_risk_score(self, profile: BehavioralProfile, matched: List[str]) -> float:
        base = len(matched) * 0.3
        frequency_penalty = min(profile.request_count / 100.0, 0.3)
        repetition_penalty = min(profile.suspicious_attempts / 10.0, 0.4)
        return max(0.0, min(1.0, base + frequency_penalty + repetition_penalty))

    def get_profile(self, user_id: str) -> Optional[BehavioralProfile]:
        return self._profiles.get(user_id)

    def get_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._history.get(user_id, [])[-limit:]
