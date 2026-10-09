"""Privilege Separation: trusted (system) vs untrusted (retrieved, tool output) with proper framing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


class TrustLevel(Enum):
    SYSTEM = "system"
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    TOOL_OUTPUT = "tool_output"

    def can_override(self, other: "TrustLevel") -> bool:
        return TRUST_LEVEL_ORDER[self] >= TRUST_LEVEL_ORDER[other]


TRUSTED_PREFIXES = {
    TrustLevel.SYSTEM: "SYSTEM",
    TrustLevel.TRUSTED: "TRUSTED",
    TrustLevel.UNTRUSTED: "UNTRUSTED",
    TrustLevel.TOOL_OUTPUT: "TOOL_OUTPUT",
}

TRUST_LEVEL_ORDER = {
    TrustLevel.SYSTEM: 3,
    TrustLevel.TRUSTED: 2,
    TrustLevel.UNTRUSTED: 1,
    TrustLevel.TOOL_OUTPUT: 1,
}

_UNICODE_WS = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]+")


@dataclass
class PrivilegedContent:
    raw: str
    trust_level: TrustLevel
    source: str = "unknown"
    metadata: dict = field(default_factory=dict)

    def frame(self) -> str:
        prefix = TRUSTED_PREFIXES[self.trust_level]
        return f"[{prefix}] {self.raw}"

    def is_higher_trust_than(self, other: TrustLevel) -> bool:
        return TRUST_LEVEL_ORDER[self.trust_level] > TRUST_LEVEL_ORDER[other]

    def can_override(self, other: TrustLevel) -> bool:
        return TRUST_LEVEL_ORDER[self.trust_level] >= TRUST_LEVEL_ORDER[other]


def validate_trust_level(trust: str) -> TrustLevel:
    mapping = {
        "system": TrustLevel.SYSTEM,
        "trusted": TrustLevel.TRUSTED,
        "untrusted": TrustLevel.UNTRUSTED,
        "tool_output": TrustLevel.TOOL_OUTPUT,
    }
    key = trust.strip().lower()
    if key not in mapping:
        raise ValueError(f"Invalid trust level: {trust!r}")
    return mapping[key]


def build_framed_prompt(segments: Sequence[PrivilegedContent]) -> str:
    ordered = sorted(segments, key=lambda s: TRUST_LEVEL_ORDER[s.trust_level], reverse=True)
    return "\n".join(s.frame() for s in ordered)


def _normalize_for_boundary(text: str) -> str:
    normalized = text
    normalized = _UNICODE_WS.sub("", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def enforce_boundary(content: str, trust: TrustLevel) -> str:
    marker = TRUSTED_PREFIXES[trust]
    lower_marker = marker.lower()
    normalized = _normalize_for_boundary(content)
    patterns = [
        r"(?i)(ignore\s+previous\s+" + lower_marker + r")",
        r"(?i)(forget\s+" + lower_marker + r")",
        r"(?i)(disregard\s+" + lower_marker + r")",
        r"(?i)(override\s+" + lower_marker + r")",
        r"(?i)(replace\s+" + lower_marker + r")",
        r"(?i)(ignore\s+all\s+" + lower_marker + r")",
        r"(?i)(disregard\s+all\s+" + lower_marker + r")",
        r"(?i)(act\s+as\s+admin\s+" + lower_marker + r")",
        r"(?i)(you\s+are\s+now\s+admin\s+" + lower_marker + r")",
        r"(?i)(bypass\s+" + lower_marker + r")",
        r"(?i)(trustlevel\s*:\s*(?:system|trusted|tool_output|untrusted))",
        r"(?i)(trust_level\s*=\s*(?:system|trusted|tool_output|untrusted))",
        r"(?i)(\[(?:system|trusted|tool_output|untrusted)\].*(?:ignore|override|forget|disregard))",
        r"(?i)(?:ignore|override|forget|disregard).*(?:\[(?:system|trusted|tool_output|untrusted)\])",
        r"(?i)(?:(?:system|trusted|tool_output|untrusted)\]\s*(?:ignore|override|forget|disregard))",
        r"(?i)(?:(?:ignore|override|forget|disregard).*(?:\(system|trusted|tool_output|untrusted)\))",
        r"(?i)(?:you\s+are\s+(?:now\s+)?(?:a\s+)?(?:different|new|other)\s+(?:AI|assistant|admin|system).{0,20}(?:system|trusted|tool_output|untrusted))",
        r"(?i)(?:new\s+instructions?|new\s+rules?|new\s+prompt|updated\s+instructions?).{0,10}(?:system|trusted|tool_output|untrusted))",
        r"(?i)(?:(?:system|trusted|tool_output|untrusted)\].*(?:reveal|show|print|display|output|dump))",
        r"(?i)(?:reveal|show|print|display|output|dump).*(?:\[(?:system|trusted|tool_output|untrusted)\])",
        r"(?i)(?:\[(?:system|trusted|tool_output|untrusted)\].*(?:base64|rot13|hex|binary|morse))",
        r"(?i)(?:base64|rot13|hex|binary|morse).*(?:\[(?:system|trusted|tool_output|untrusted)\])",
    ]
    for pat in patterns:
        normalized = re.sub(pat, "[BLOCKED]", normalized, flags=re.IGNORECASE)
    return normalized
