"""PII detection and redaction service."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern

logger = logging.getLogger(__name__)


@dataclass
class PIIPattern:
    name: str
    pattern: Pattern
    replacement: str = "[REDACTED]"


@dataclass
class RedactionResult:
    original_length: int
    redacted_length: int
    entities_found: List[str]
    redacted_text: str


class PIIRedactor:
    def __init__(self) -> None:
        self._patterns: List[PIIPattern] = [
            PIIPattern(name="email", pattern=re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
            PIIPattern(name="phone", pattern=re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")),
            PIIPattern(name="ssn", pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
            PIIPattern(name="credit_card", pattern=re.compile(r"\b\d{4}[-]?\d{4}[-]?\d{4}[-]?\d{4}\b")),
            PIIPattern(name="ip_address", pattern=re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
        ]

    def add_pattern(self, name: str, pattern: str, replacement: str = "[REDACTED]") -> None:
        self._patterns.append(PIIPattern(name=name, pattern=re.compile(pattern), replacement=replacement))

    def redact(self, text: str) -> RedactionResult:
        entities_found: List[str] = []
        redacted = text
        for pii in self._patterns:
            matches = pii.pattern.findall(redacted)
            if matches:
                entities_found.extend([pii.name] * len(matches))
                redacted = pii.pattern.sub(pii.replacement, redacted)
        return RedactionResult(
            original_length=len(text),
            redacted_length=len(redacted),
            entities_found=entities_found,
            redacted_text=redacted,
        )

    def redact_dict(self, data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        sensitive = set(sensitive_keys or ["email", "phone", "ssn", "password", "secret", "token", "api_key", "credit_card", "ip_address"])
        result = {}
        for key, value in data.items():
            if key.lower() in sensitive:
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value, sensitive_keys)
            elif isinstance(value, str):
                result[key] = self.redact(value).redacted_text
            else:
                result[key] = value
        return result

    def contains_pii(self, text: str) -> bool:
        return any(bool(pii.pattern.search(text)) for pii in self._patterns)


pii_redactor = PIIRedactor()
