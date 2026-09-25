"""Enhanced PII detection and redaction."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PIIMatch:
    pii_type: str
    value: str
    start: int
    end: int
    confidence: float
    replacement: str


class PIIGuard:
    """Detect and redact PII from text."""

    PATTERNS = {
        "email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
        "phone_us": (r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b", "[PHONE_REDACTED]"),
        "phone_intl": (r"\+\d{1,3}[-.\s]?\d{1,14}\b", "[PHONE_REDACTED]"),
        "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
        "credit_card": (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[CREDIT_CARD_REDACTED]"),
        "ip_address": (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_REDACTED]"),
        "date_of_birth": (r"\b(?:0?[1-9]|1[0-2])[/\-](?:0?[1-9]|[12]\d|3[01])[/\-]\d{4}\b", "[DOB_REDACTED]"),
        "api_key": (r"\b(?:sk|api|key|token|secret)[-_]?[a-zA-Z0-9]{16,}\b", "[API_KEY_REDACTED]"),
        "password": (r"\b(?:password|passwd|pwd)\s*[:=]\s*\S+\b", "[PASSWORD_REDACTED]"),
        "address": (r"\b\d{1,5}\s+[A-Za-z0-9\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr)\b", "[ADDRESS_REDACTED]"),
        "iban": (r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b", "[IBAN_REDACTED]"),
        "swift": (r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b", "[SWIFT_REDACTED]"),
    }

    def __init__(self):
        self._compiled = {}
        for pii_type, (pattern, replacement) in self.PATTERNS.items():
            self._compiled[pii_type] = (re.compile(pattern, re.IGNORECASE), replacement)

    def detect(self, text: str) -> list[PIIMatch]:
        matches = []
        for pii_type, (pattern, _) in self._compiled.items():
            for match in pattern.finditer(text):
                confidence = self._estimate_confidence(pii_type, match.group())
                matches.append(PIIMatch(
                    pii_type=pii_type,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                    replacement=self.PATTERNS[pii_type][1],
                ))
        matches.sort(key=lambda m: m.start)
        return matches

    def _estimate_confidence(self, pii_type: str, value: str) -> float:
        if pii_type == "email":
            return 0.95 if "@" in value and "." in value.split("@")[-1] else 0.7
        if pii_type == "ssn":
            return 0.9
        if pii_type == "credit_card":
            return 0.85
        if pii_type == "phone_us" or pii_type == "phone_intl":
            return 0.8
        return 0.75

    def redact(self, text: str, store_mappings: bool = True) -> tuple[str, list[PIIMatch]]:
        matches = self.detect(text)
        if not matches:
            return text, []

        redacted = text
        offset = 0
        for match in matches:
            start = match.start + offset
            end = match.end + offset
            redacted = redacted[:start] + match.replacement + redacted[end:]
            offset += len(match.replacement) - (match.end - match.start)

        if matches:
            logger.warning("PII detected and redacted: %s", [m.pii_type for m in matches])

        return redacted, matches

    def has_pii(self, text: str) -> bool:
        return len(self.detect(text)) > 0

    def get_pii_summary(self, text: str) -> dict:
        matches = self.detect(text)
        types = {}
        for m in matches:
            types[m.pii_type] = types.get(m.pii_type, 0) + 1
        return {
            "has_pii": len(matches) > 0,
            "count": len(matches),
            "types": types,
            "max_confidence": max((m.confidence for m in matches), default=0.0),
        }


pii_guard = PIIGuard()
