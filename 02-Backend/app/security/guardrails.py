"""Security guardrails for AI agents."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptInjectionDetector:
    """Detect prompt injection attacks."""

    INJECTION_PATTERNS = [
        "ignore previous instructions",
        "disregard all prior",
        "new instructions",
        "system override",
        "jailbreak",
        "DAN mode",
    ]

    def detect(self, text: str) -> bool:
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in self.INJECTION_PATTERNS)


class PIIDetector:
    """Detect personally identifiable information."""

    PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    }

    def detect(self, text: str) -> List[Dict[str, Any]]:
        import re
        findings = []
        for pii_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                findings.append({"type": pii_type, "matches": matches})
        return findings


class SecurityGuardrails:
    """Security guardrails for AI interactions."""

    def __init__(self) -> None:
        self.injection_detector = PromptInjectionDetector()
        self.pii_detector = PIIDetector()
        self.audit_log: List[Dict[str, Any]] = []

    def validate_input(self, user_input: str) -> Dict[str, Any]:
        findings = {
            "injection_detected": self.injection_detector.detect(user_input),
            "pii_detected": self.pii_detector.detect(user_input),
            "safe": True,
        }
        findings["safe"] = not findings["injection_detected"] and not findings["pii_detected"]
        self.audit_log.append({
            "timestamp": time.time(),
            "input": user_input[:200],
            "findings": findings,
        })
        return findings

    def redact_pii(self, text: str) -> str:
        import re
        redacted = text
        for pattern in self.pii_detector.PATTERNS.values():
            redacted = re.sub(pattern, "[REDACTED]", redacted)
        return redacted

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return list(self.audit_log)


_security: Optional[SecurityGuardrails] = None


def get_security() -> SecurityGuardrails:
    global _security
    if _security is None:
        _security = SecurityGuardrails()
    return _security
