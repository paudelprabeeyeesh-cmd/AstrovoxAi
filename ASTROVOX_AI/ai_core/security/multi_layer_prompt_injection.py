"""Multi-layer prompt injection defense for ASTROVOX AI."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
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
class DefenseFinding:
    layer: DefenseLayer
    matched: Optional[str]
    confidence: float
    action: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiLayerPromptInjectionDefense:
    """Multi-layer prompt injection defense."""

    def __init__(self):
        self._blocked_patterns = [
            re.compile(r"ignore\s+(all\s+)?(previous\s+)?instructions", re.IGNORECASE),
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
        ]
        self._blocked_hashes: Set[str] = set()
        self._history: Dict[str, List[str]] = {}

    def defend(self, text: str, user_id: str = "anonymous") -> List[DefenseFinding]:
        findings: List[DefenseFinding] = []
        for pattern in self._blocked_patterns:
            match = pattern.search(text)
            if match:
                findings.append(DefenseFinding(
                    layer=DefenseLayer.PATTERN_DETECTION,
                    matched=match.group(),
                    confidence=0.9,
                    action="block",
                ))
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        if text_hash in self._blocked_hashes:
            findings.append(DefenseFinding(
                layer=DefenseLayer.OUTPUT_FILTERING,
                matched=None,
                confidence=1.0,
                action="block",
                metadata={"reason": "previously_blocked"},
            ))
        self._history.setdefault(user_id, []).append(text)
        return findings

    def is_safe(self, text: str, user_id: str = "anonymous") -> bool:
        return not any(f.action == "block" for f in self.defend(text, user_id))

    def sanitize(self, text: str) -> str:
        for pattern in self._blocked_patterns:
            text = pattern.sub("[REDACTED]", text)
        return text
