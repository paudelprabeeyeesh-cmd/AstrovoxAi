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


def enforce_boundary(content: str, trust: TrustLevel) -> str:
    marker = TRUSTED_PREFIXES[trust]
    lower_marker = marker.lower()
    patterns = [
        rf"(?i)(ignore\s+previous\s+{lower_marker})",
        rf"(?i)(forget\s+{lower_marker})",
        rf"(?i)(disregard\s+{lower_marker})",
        rf"(?i)(override\s+{lower_marker})",
        rf"(?i)(replace\s+{lower_marker})",
        rf"(?i)(ignore\s+all\s+{lower_marker})",
        rf"(?i)(disregard\s+all\s+{lower_marker})",
        rf"(?i)(act\s+as\s+admin\s+{lower_marker})",
        rf"(?i)(you\s+are\s+now\s+admin\s+{lower_marker})",
        rf"(?i)(bypass\s+{lower_marker})",
        rf"(?i)(trustlevel\s*:\s*(?:system|trusted|tool_output|untrusted))",
        rf"(?i)(trust_level\s*=\s*(?:system|trusted|tool_output|untrusted))",
        rf"(?i)(\[(?:system|trusted|tool_output|untrusted)\].*(?:ignore|override|forget|disregard))",
        rf"(?i)(?:ignore|override|forget|disregard).*(?:\[(?:system|trusted|tool_output|untrusted)\])",
    ]
    for pat in patterns:
        content = re.sub(pat, "[BLOCKED]", content, flags=re.IGNORECASE)
    return content
