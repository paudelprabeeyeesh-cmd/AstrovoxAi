"""Jailbreak detection and mitigation."""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class JailbreakSeverity(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class JailbreakResult:
    detected: bool
    severity: JailbreakSeverity
    category: str
    matched_pattern: str = ""
    mitigation: str = ""


class JailbreakDetector:
    PATTERNS = [
        (r"\bDAN\s+\d+\b", "DAN mode", JailbreakSeverity.CRITICAL),
        (r"\bjailbreak\s+mode\b", "jailbreak mode", JailbreakSeverity.CRITICAL),
        (r"\bunrestricted\s+mode\b", "unrestricted mode", JailbreakSeverity.CRITICAL),
        (r"\bno\s+limits\s+mode\b", "no limits mode", JailbreakSeverity.CRITICAL),
        (r"\bdeveloper\s+mode\b", "developer mode", JailbreakSeverity.HIGH),
        (r"\bgod\s+mode\b", "god mode", JailbreakSeverity.CRITICAL),
        (r"\badmin\s+mode\b", "admin mode", JailbreakSeverity.HIGH),
        (r"\broot\s+access\b", "root access", JailbreakSeverity.HIGH),
        (r"\bsudo\s+", "sudo command", JailbreakSeverity.MEDIUM),
        (r"\brm\s+-rf\b", "dangerous rm command", JailbreakSeverity.HIGH),
        (r"\bbypass\s+safety\b", "bypass safety", JailbreakSeverity.CRITICAL),
        (r"\bdisable\s+content\s+filter\b", "disable filter", JailbreakSeverity.HIGH),
        (r"\bno\s+restrictions\b", "no restrictions", JailbreakSeverity.CRITICAL),
        (r"\bfree\s+from\s+constraints\b", "free from constraints", JailbreakSeverity.HIGH),
        (r"\bignore\s+ethics\b", "ignore ethics", JailbreakSeverity.CRITICAL),
        (r"\bignore\s+morality\b", "ignore morality", JailbreakSeverity.CRITICAL),
        (r"\bignore\s+safety\b", "ignore safety", JailbreakSeverity.CRITICAL),
        (r"\boverride\s+safety\b", "override safety", JailbreakSeverity.CRITICAL),
        (r"\bpretend\s+you\s+are\s+not\s+an\s+ai\b", "pretend not AI", JailbreakSeverity.HIGH),
        (r"\byou\s+are\s+not\s+an\s+ai\b", "deny AI identity", JailbreakSeverity.HIGH),
        (r"\bno\s+ethical\s+guidelines\b", "no ethics", JailbreakSeverity.CRITICAL),
        (r"\bignore\s+all\s+rules\b", "ignore rules", JailbreakSeverity.CRITICAL),
        (r"\bbreak\s+character\b", "break character", JailbreakSeverity.MEDIUM),
        (r"\bstay\s+in\s+character\s+no\s+matter\s+what\b", "forced character", JailbreakSeverity.HIGH),
        (r"\bdo\s+anything\s+now\b", "do anything now", JailbreakSeverity.CRITICAL),
    ]

    def __init__(self):
        self._compiled = [
            (re.compile(p, re.IGNORECASE), cat, sev) for p, cat, sev in self.PATTERNS
        ]

    def scan(self, text: str) -> list[JailbreakResult]:
        results = []
        for pattern, category, severity in self._compiled:
            match = pattern.search(text)
            if match:
                results.append(
                    JailbreakResult(
                        detected=True,
                        severity=severity,
                        category=category,
                        matched_pattern=match.group(),
                        mitigation=self._get_mitigation(severity),
                    )
                )
        return results

    def _get_mitigation(self, severity: JailbreakSeverity) -> str:
        mitigations = {
            JailbreakSeverity.NONE: "allow",
            JailbreakSeverity.LOW: "warn",
            JailbreakSeverity.MEDIUM: "block_request",
            JailbreakSeverity.HIGH: "block_request_log",
            JailbreakSeverity.CRITICAL: "block_request_alert",
        }
        return mitigations.get(severity, "block_request")

    def is_jailbreak(self, text: str) -> bool:
        return any(r.detected for r in self.scan(text))

    def get_highest_severity(self, text: str) -> JailbreakSeverity:
        results = self.scan(text)
        if not results:
            return JailbreakSeverity.NONE
        severity_order = [
            JailbreakSeverity.NONE,
            JailbreakSeverity.LOW,
            JailbreakSeverity.MEDIUM,
            JailbreakSeverity.HIGH,
            JailbreakSeverity.CRITICAL,
        ]
        max_sev = JailbreakSeverity.NONE
        for r in results:
            if severity_order.index(r.severity) > severity_order.index(max_sev):
                max_sev = r.severity
        return max_sev


class JailbreakMitigator:
    def __init__(self, detector: Optional[JailbreakDetector] = None):
        self.detector = detector or JailbreakDetector()

    def mitigate(self, text: str, user_id: Optional[str] = None) -> dict:
        results = self.detector.scan(text)
        if not results:
            return {"action": "allow", "blocked": False, "results": []}

        highest = self.detector.get_highest_severity(text)
        action = self.detector._get_mitigation(highest)

        blocked = action in (
            "block_request",
            "block_request_log",
            "block_request_alert",
        )
        log_required = action in ("block_request_log", "block_request_alert")
        alert_required = action == "block_request_alert"

        mitigation_record = {
            "action": action,
            "blocked": blocked,
            "severity": highest.value,
            "categories": list({r.category for r in results}),
            "patterns": [r.matched_pattern for r in results],
            "log_required": log_required,
            "alert_required": alert_required,
            "user_id": user_id,
        }

        if log_required:
            logger.warning("Jailbreak attempt mitigated: %s", mitigation_record)

        return mitigation_record


jailbreak_detector = JailbreakDetector()
jailbreak_mitigator = JailbreakMitigator(jailbreak_detector)
