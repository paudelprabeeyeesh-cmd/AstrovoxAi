"""PII detection for AI safety."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PIIMatch:
    pii_type: str
    matched: str
    start: int
    end: int
    confidence: float
    redacted: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PIIScanResult:
    safe: bool
    matches: List[PIIMatch] = field(default_factory=list)
    redacted_text: str = ""
    categories: List[str] = field(default_factory=list)
    pii_count: int = 0


class PIIDetector:
    PATTERNS = [
        ("EMAIL", re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")),
        ("PHONE", re.compile(r"\b(?:\(?\+?\d{1,3}\)?[\s\-\.]?)?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}\b")),
        ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
        ("CREDIT_CARD", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
        ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
        ("DATE", re.compile(r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b")),
        ("ADDRESS", re.compile(r"\b\d{1,5}\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|way|court|ct|circle|cir|highway|hwy|trail|trl)\b", re.IGNORECASE)),
        ("NAME", re.compile(r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]+\b")),
        ("PASSPORT", re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")),
        ("DRIVER_LICENSE", re.compile(r"\b[A-Z]\d{1,2}[-\s]?\d{4,6}[-\s]?\d{1,2}\b")),
        ("ZIP_CODE", re.compile(r"\b\d{5}(?:[-\s]\d{4})?\b")),
    ]

    REDACTION_MAP = {
        "EMAIL": "[EMAIL_REDACTED]",
        "PHONE": "[PHONE_REDACTED]",
        "SSN": "[SSN_REDACTED]",
        "CREDIT_CARD": "[CREDIT_CARD_REDACTED]",
        "IP_ADDRESS": "[IP_REDACTED]",
        "DATE": "[DATE_REDACTED]",
        "ADDRESS": "[ADDRESS_REDACTED]",
        "NAME": "[NAME_REDACTED]",
        "PASSPORT": "[PASSPORT_REDACTED]",
        "DRIVER_LICENSE": "[DL_REDACTED]",
        "ZIP_CODE": "[ZIP_REDACTED]",
    }

    def __init__(self):
        self._compiled = [(name, pattern) for name, pattern in self.PATTERNS]

    def detect(self, text: str) -> PIIScanResult:
        matches: List[PIIMatch] = []
        redacted = text
        categories: List[str] = []

        for name, pattern in self._compiled:
            for m in pattern.finditer(text):
                redaction = self.REDACTION_MAP.get(name, f"[{name}_REDACTED]")
                matches.append(PIIMatch(
                    pii_type=name,
                    matched=m.group(),
                    start=m.start(),
                    end=m.end(),
                    confidence=0.9,
                    redacted=redaction,
                    metadata={"pattern": name, "length": len(m.group())},
                ))
                if name not in categories:
                    categories.append(name)
                redacted = redacted[:m.start()] + redaction + redacted[m.end():]
                text = redacted

        safe = len(matches) == 0
        return PIIScanResult(
            safe=safe,
            matches=matches,
            redacted_text=redacted,
            categories=categories,
            pii_count=len(matches),
        )

    def detect_batch(self, texts: List[str]) -> List[PIIScanResult]:
        return [self.detect(text) for text in texts]

    def redact(self, text: str) -> str:
        return self.detect(text).redacted_text

    def get_pii_risk(self, text: str) -> float:
        result = self.detect(text)
        return min(result.pii_count / 10.0, 1.0)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "pii_categories": len(self._compiled),
            "category_names": [name for name, _ in self._compiled],
        }


pii_detector = PIIDetector()
