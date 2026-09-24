import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class NormalizedObservation:
    original: str
    normalized: str
    truncated: bool
    preserved_tokens: List[str]
    token_count: int


class ObservationNormalizer:
    def __init__(self, max_length: int = 500, preserve_patterns: Optional[List[str]] = None):
        self.max_length = max_length
        self.preserve_patterns = preserve_patterns or [
            r'\b\d+\.?\d*\b',
            r'\b[A-Z][A-Z]+\b',
            r'"(?:[^"\\]|\\.)*"',
            r"'(?:[^'\\]|\\.)*'",
        ]

    def normalize(self, raw_output: str, tool_name: str) -> NormalizedObservation:
        preserved = self._extract_preserved(raw_output)
        cleaned = self._clean(raw_output)
        normalized, truncated = self._truncate(cleaned, self.max_length)
        normalized = self._reintegrate_preserved(normalized, preserved)
        return NormalizedObservation(
            original=raw_output,
            normalized=normalized,
            truncated=truncated,
            preserved_tokens=preserved,
            token_count=len(normalized.split()),
        )

    def _extract_preserved(self, text: str) -> List[str]:
        tokens: List[str] = []
        for pattern in self.preserve_patterns:
            tokens.extend(re.findall(pattern, text))
        return tokens

    def _clean(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _truncate(self, text: str, max_len: int) -> tuple[str, bool]:
        if len(text) <= max_len:
            return text, False
        truncated = text[:max_len]
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]
        return truncated + "...", True

    def _reintegrate_preserved(self, text: str, preserved: List[str]) -> str:
        for token in preserved:
            if token not in text:
                text = text.rstrip("...") + f" ... [{token}]"
        return text
