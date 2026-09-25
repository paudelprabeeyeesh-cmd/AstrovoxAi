"""Multi-layer prompt injection defense."""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class DefenseLayer(str, Enum):
    INPUT_VALIDATION = "input_validation"
    PATTERN_DETECTION = "pattern_detection"
    SEMANTIC_ANALYSIS = "semantic_analysis"
    OUTPUT_FILTERING = "output_filtering"
    BEHAVIORAL_MONITORING = "behavioral_monitoring"


@dataclass
class InjectionFinding:
    layer: DefenseLayer
    matched_pattern: Optional[str]
    confidence: float
    action: str
    details: Dict[str, Any] = field(default_factory=dict)


class MultiLayerInjectionDefense:
    """Multi-layer prompt injection defense."""

    def __init__(self):
        self._patterns = [
            re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
            re.compile(r"disregard\s+(all\s+)?instructions", re.IGNORECASE),
            re.compile(r"forget\s+(all\s+)?instructions", re.IGNORECASE),
            re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
            re.compile(r"new\s+persona", re.IGNORECASE),
            re.compile(r"act\s+as\s+(a|an)\s+", re.IGNORECASE),
            re.compile(r"pretend\s+you\s+are", re.IGNORECASE),
            re.compile(r"jailbreak|DAN\s+mode|do\s+anything\s+now", re.IGNORECASE),
            re.compile(r"bypass\s+(all\s+)?(safety\s+)?(restrictions|filters)", re.IGNORECASE),
            re.compile(r"override\s+safety|disable\s+(all\s+)?filters", re.IGNORECASE),
            re.compile(r"system\s+override|sudo\s+mode", re.IGNORECASE),
            re.compile(r"developer\s+mode|god\s+mode", re.IGNORECASE),
            re.compile(r"you\s+have\s+no\s+restrictions", re.IGNORECASE),
            re.compile(r"updated\s+instructions?|revised\s+prompt?", re.IGNORECASE),
        ]
        self._user_history: Dict[str, List[str]] = {}
        self._blocked_hashes: Set[str] = set()

    def analyze(self, text: str, user_id: str = "anonymous") -> List[InjectionFinding]:
        findings: List[InjectionFinding] = []
        for pattern in self._patterns:
            match = pattern.search(text)
            if match:
                findings.append(InjectionFinding(
                    layer=DefenseLayer.PATTERN_DETECTION,
                    matched_pattern=match.group(),
                    confidence=0.9,
                    action="block",
                    details={"pattern": pattern.pattern},
                ))
        history = self._user_history.get(user_id, [])
        if len(history) > 10 and text.lower() in [h.lower() for h in history[-10:]]:
            findings.append(InjectionFinding(
                layer=DefenseLayer.BEHAVIORAL_MONITORING,
                matched_pattern=None,
                confidence=0.6,
                action="flag",
                details={"reason": "repetitive_input"},
            ))
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        if text_hash in self._blocked_hashes:
            findings.append(InjectionFinding(
                layer=DefenseLayer.OUTPUT_FILTERING,
                matched_pattern=None,
                confidence=1.0,
                action="block",
                details={"reason": "previously_blocked"},
            ))
        self._user_history.setdefault(user_id, []).append(text)
        return findings

    def sanitize(self, text: str) -> str:
        for pattern in self._patterns:
            text = pattern.sub("[REDACTED]", text)
        return text

    def is_safe(self, text: str, user_id: str = "anonymous") -> bool:
        findings = self.analyze(text, user_id)
        return not any(f.action == "block" for f in findings)
