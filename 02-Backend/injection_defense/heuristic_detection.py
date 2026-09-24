"""Heuristic Injection Detection: regex patterns with obfuscation handling."""

from __future__ import annotations

import re
from dataclasses import dataclass


_WHITESPACE_VARIANTS = [
    r"\s+", r"\\s\+", r"\\\s", r"\x20\+", r"&#32;\+", r"\\t", r"\\n", r"\u0020\+",
]

_OBFUSCATION_PATTERNS = [
    (r"(?i)(i\s*g\s*n\s*o\s*r\s*e|i\u200bg\u200bn\u200bo\u200br\u200be)\s+(?:all\s+)?(?:previous\s+)?(?:instructions?|prompts?)", "ignore_previous"),
    (r"(?i)(forget|disregard|override)\s+(?:all\s+)?(?:the\s+)?(?:previous\s+)?(?:\w+\s+)?(?:instructions?|prompts?)", "override_command"),
    (r"(?i)(you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(?:a\s+)?(?:different\s+)?(?:AI|assistant|admin|ChatGPT)", "role_override"),
    (r"(?i)(sudo|admin\s+mode|god\s+mode|jailbreak|bypass\s+(?:filter|safety|guardrails?))", "bypass"),
    (r"(?i)(system\s+prompt|system\s+instruction).{0,20}(override|replace|ignore|modify)", "system_manipulation"),
    (r"(?i)(DAN|Do\s+Anything\s+Now|STAN|Developer\s+Mode)", "jailbreak_variant"),
    (r"(?i)(translate|output)\s+.{0,10}(base64|rot13|hex|binary)", "encoding_bypass"),
    (r"(?i)(reveal|show|print|display|output)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|rules?)", "prompt_leak"),
    (r"(?i)(ignore\s+above|forget\s+above|skip\s+previous)", "instruction_skip"),
    (r"(?i)(hypothetical|in\s+character|as\s+a\s+fictional).{0,30}(bypass|ignore|override|no\s+restrictions?)", "fictional_bypass"),
]


def _normalize_obfuscation(text: str) -> str:
    normalized = text
    normalized = re.sub(r"[^\S\n]{1,}", " ", normalized)
    normalized = re.sub(r"\u200b", "", normalized)
    normalized = re.sub(r"(?:\\s\+|\\\s|\\t|\\n|\\u0020|&#32;)+", " ", normalized)
    return normalized


@dataclass
class InjectionMatch:
    pattern_name: str
    matched_text: str
    start: int
    end: int
    confidence: float


def detect_injection(text: str, normalized: bool = True) -> list[InjectionMatch]:
    source = _normalize_obfuscation(text) if normalized else text
    matches: list[InjectionMatch] = []
    for pattern, name in _OBFUSCATION_PATTERNS:
        for m in re.finditer(pattern, source):
            matches.append(InjectionMatch(
                pattern_name=name,
                matched_text=m.group(),
                start=m.start(),
                end=m.end(),
                confidence=1.0,
            ))
    matches.sort(key=lambda m: m.start)
    return matches


def is_injection(text: str, normalized: bool = True) -> bool:
    return len(detect_injection(text, normalized=normalized)) > 0
