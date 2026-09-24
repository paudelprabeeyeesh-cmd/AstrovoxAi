import re
from typing import Any

import numpy as np


class PIIRegexScrubber:
    _PATTERNS: dict[str, re.Pattern[str]] = {}

    @classmethod
    def _get_patterns(cls) -> dict[str, re.Pattern[str]]:
        if not cls._PATTERNS:
            cls._PATTERNS = {
                "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
                "phone": re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
                "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            }
        return cls._PATTERNS

    @classmethod
    def find(cls, text: str) -> dict[str, list[str]]:
        patterns = cls._get_patterns()
        results = {name: pat.findall(text) for name, pat in patterns.items()}
        return {k: v for k, v in results.items() if v}

    @classmethod
    def redact(cls, text: str, replacement: str = "[REDACTED]") -> str:
        patterns = cls._get_patterns()
        for name, pat in patterns.items():
            text = pat.sub(replacement, text)
        return text


class NERScrubber:
    def __init__(self, labels: list[str] | None = None) -> None:
        self.labels = labels or ["EMAIL", "PHONE", "SSN"]

    def find(self, text: str) -> list[dict[str, Any]]:
        entities = []
        for label in self.labels:
            if label == "EMAIL":
                m = re.finditer(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
            elif label == "PHONE":
                m = re.finditer(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
            elif label == "SSN":
                m = re.finditer(r"\b\d{3}-\d{2}-\d{4}\b", text)
            else:
                continue
            for match in m:
                entities.append({"label": label, "start": match.start(), "end": match.end(), "text": match.group(0)})
        return entities
