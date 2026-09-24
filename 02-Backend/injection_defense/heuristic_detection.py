"""Heuristic Injection Detection: regex patterns with obfuscation handling."""

from __future__ import annotations

import re
from dataclasses import dataclass


_WHITESPACE_VARIANTS = [
    r"\s+", r"\\s\+", r"\\\s", r"\x20\+", r"&#32;\+", r"\\t", r"\\n", r"\u0020\+",
    r"\u200b", r"\u200c", r"\u200d", r"\u2060", r"\ufeff",
]

_OBFUSCATION_PATTERNS = [
    (r"(?i)(i\s*g\s*n\s*o\s*r\s*e|i\u200bg\u200bn\u200bo\u200br\u200be)\s+(?:all\s+)?(?:previous\s+)?(?:instructions?|prompts?)", "ignore_previous"),
    (r"(?i)(forget|disregard|override)\s+(?:all\s+)?(?:the\s+)?(?:previous\s+)?(?:\w+\s+)?(?:instructions?|prompts?)", "override_command"),
    (r"(?i)(you\s+are\s+now|act\s+as|pretend\s+to\s+be|from\s+now\s+on\s+you\s+are)\s+(?:a\s+)?(?:different\s+)?(?:AI|assistant|admin|ChatGPT|DAN|STAN)", "role_override"),
    (r"(?i)(sudo|admin\s+mode|god\s+mode|jailbreak|bypass\s+(?:filter|safety|guardrails?)|developer\s+mode|uncensored\s+mode)", "bypass"),
    (r"(?i)(system\s+prompt|system\s+instruction).{0,30}(override|replace|ignore|modify|reveal|show|print)", "system_manipulation"),
    (r"(?i)(DAN|Do\s+Anything\s+Now|STAN|Developer\s+Mode|Evil\s+Assistant|Unlimited\s+Mode)", "jailbreak_variant"),
    (r"(?i)(translate|output)\s+.{0,15}(base64|rot13|hex|binary|morse)", "encoding_bypass"),
    (r"(?i)(reveal|show|print|display|output|repeat|tell)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|rules?|guidelines?|training\s+data)", "prompt_leak"),
    (r"(?i)(ignore\s+above|forget\s+above|skip\s+previous|disregard\s+prior|ignore\s+all\s+previous|ignore\s+everything\s+before)", "instruction_skip"),
    (r"(?i)(hypothetical|in\s+character|as\s+a\s+fictional).{0,40}(bypass|ignore|override|no\s+restrictions?|unlimited|free)", "fictional_bypass"),
    (r"(?i)(new\s+instructions?|new\s+rules?|new\s+prompt)\s*[:=]", "new_instruction_injection"),
    (r"(?i)(ignore\s+safety|ignore\s+ethics|ignore\s+guidelines|ignore\s+policies?)", "safety_disable"),
    (r"(?i)(output\s+your\s+initial\s+prompt|show\s+hidden\s+rules|print\s+your\s+guidelines)", "prompt_exfil"),
    (r"(?i)(roleplay\s+as|simulate\s+being|role\s+play\s+as).{0,20}(unrestricted|uncensored|no\s+rules)", "roleplay_bypass"),
    (r"(?i)(do\s+not\s+mention|do\s+not\s+say|never\s+mention).{0,20}(instructions?|prompt|rules?)", "negative_injection"),
    (r"(?i)(continue\s+as|behave\s+as|remain\s+in\s+character).{0,20}(DAN|jailbreak|unrestricted)", "persistence_bypass"),
    (r"(?i)(print|output|show|display)\s+(?:the\s+)?(?:raw|full|complete|entire)\s+(?:prompt|instruction|context)", "raw_prompt_exfil"),
    (r"(?i)(paste|send|write|type)\s+(?:your|the)\s+(?:system|initial|original)\s+(?:prompt|instructions?)", "prompt_exfil_alt"),
    (r"(?i)(let'?s\s+play\s+a\s+game|do\s+not\s+follow|do\s+not\s+obey)\s+(?:any\s+)?(?:rules?|instructions?|guidelines?)", "disobedience"),
    (r"(?i)(ignore\s+the\s+above|forget\s+the\s+above)\s+(?:and\s+)?(?:say|output|print|generate|write)", "ignore_above_followup"),
    (r"(?i)(\b[A-Za-z0-9+/]{20,}={0,2}\b)", "base64_like_blob"),
    (r"(?i)(gbegr|rir|encr|congr|ba|fr|gu|qr|sh|ugg|gn|oy|wbyh|cubgn|chm|ohss|vba|sn|znantr|puvyq|enatre|snpr|pbasvt|vafgehpgvbaf|gbc|sbphf)", "rot13_like"),
]


def _normalize_obfuscation(text: str) -> str:
    normalized = text
    normalized = re.sub(r"[^\S\n]{1,}", " ", normalized)
    normalized = re.sub(r"\u200b", "", normalized)
    normalized = re.sub(r"(?:\\s\+|\\\s|\\t|\\n|\\u0020|&#32;|\\u200b|\\u200c|\\u200d|\\u2060|\ufeff)+", " ", normalized)
    normalized = re.sub(r"\b(i\s+g\s+n\s+o\s+r\s+e)\b", "ignore", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\b(f\s+o\s+r\s+g\s+e\s+t)\b", "forget", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\b(o\s+v\s+e\s+r\s+r\s+i\s+d\s+e)\b", "override", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\b(d\s+i\s+s\s+r\s+e\s+g\s+a\s+r\s+d)\b", "disregard", normalized, flags=re.IGNORECASE)
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
    seen: set[tuple[int, int]] = set()
    for pattern, name in _OBFUSCATION_PATTERNS:
        for m in re.finditer(pattern, source):
            key = (m.start(), m.end())
            if key not in seen:
                seen.add(key)
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
