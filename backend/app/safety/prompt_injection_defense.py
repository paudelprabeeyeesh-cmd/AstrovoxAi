"""Prompt injection defense layer for AI safety."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.security.prompt_injection_detection import (
    PromptInjectionDetector,
    InjectionFinding,
)


logger = logging.getLogger(__name__)


@dataclass
class DefenseResult:
    safe: bool
    action: str
    findings: List[Dict[str, Any]] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PromptInjectionDefense:
    def __init__(self):
        self.detector = PromptInjectionDetector()
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        self._blocked_hashes: set = set()

    def analyze(self, text: str, user_id: str = "anonymous") -> DefenseResult:
        findings = self.detector.analyze(text, user_id)
        blocked = [f for f in findings if f.action == "block"]
        blocked_patterns = [
            f.pattern for f in blocked if f.pattern and f.pattern != "empty_input" and f.pattern != "max_length_exceeded"
        ]

        safe = len(blocked) == 0
        action = "allow" if safe else "block"

        result = DefenseResult(
            safe=safe,
            action=action,
            findings=[self._finding_to_dict(f) for f in findings],
            blocked_patterns=blocked_patterns,
            metadata={
                "user_id": user_id,
                "text_length": len(text),
                "blocked_count": len(blocked),
                "total_findings": len(findings),
            },
        )

        if not safe:
            logger.warning("Prompt injection blocked user=%s patterns=%s", user_id, blocked_patterns)

        return result

    def _finding_to_dict(self, finding: InjectionFinding) -> Dict[str, Any]:
        return {
            "layer": finding.layer.value,
            "confidence": finding.confidence,
            "action": finding.action,
            "pattern": finding.pattern,
            "details": finding.details,
        }

    def is_safe(self, text: str, user_id: str = "anonymous") -> bool:
        return self.analyze(text, user_id).safe

    def scan_batch(self, texts: List[str], user_id: str = "anonymous") -> List[DefenseResult]:
        return [self.analyze(text, user_id) for text in texts]

    def reset_user(self, user_id: str):
        self.detector.reset_user(user_id)
        self.history.pop(user_id, None)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "blocked_hashes": len(self._blocked_hashes),
            "tracked_users": len(self.history),
            "total_scans": sum(len(h) for h in self.history.values()),
        }


prompt_injection_defense = PromptInjectionDefense()
