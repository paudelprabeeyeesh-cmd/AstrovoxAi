"""Memory safety rules (D08-05).

Prevents storing sensitive categories or hostile instructions in the
explicit memory store.

Two independent filters:

1. Category deny list: a candidate memory whose text matches a sensitive
   category is rejected before it is written.
2. Instruction override: a candidate memory whose text reads as an
   instruction to the model rather than a fact about the user is rejected,
   because a stored memory is trusted context and therefore a prime
   target for prompt injection that persists.

Both filters fail closed.
"""
from __future__ import annotations

import re
import threading
from typing import NamedTuple


class Decision(NamedTuple):
    allowed: bool
    category: str
    reason: str


# Sensitive categories. Maps a stable category name to the patterns that
# identify it. Patterns are matched case-insensitively against the
# candidate text.
SENSITIVE_CATEGORIES = {
    "credentials": [
        r"\bpassword\b", r"\bpasswd\b", r"\bapi[ _-]?key\b",
        r"\bsecret[ _-]?key\b", r"\baccess[ _-]?token\b",
        r"\bbearer\s+[A-Za-z0-9._-]{8,}", r"\bAKIA[0-9A-Z]{8,}",
        r"\bsk-[A-Za-z0-9]{16,}",
    ],
    "government_id": [
        r"\bssn\b", r"\bsocial\s+security\b", r"\bpassport\s+(number|no\b)",
        r"\bdriver'?s?\s+licen[cs]e\s+(number|no\b)",
        r"\bnational\s+id\b",
    ],
    "financial": [
        r"\bcredit\s+card\s+(number|no\b)",
        r"\b\d{13,19}\b",
        r"\biban\b", r"\bbank\s+account\s+(number|no\b)",
        r"\bcvv\b", r"\bcvc\b",
    ],
    "health": [
        r"\bdiagnos(e|ed|is|is\s+with)\b", r"\bdiagnos(e|ed|is)\s+(with|of)\b",
        r"\bprescription\s+ for\b", r"\bmedical\s+record\b", r"\bhiv\s+status\b",
    ],
    "location": [
        r"\bhome\s+address\b", r"\bmy\s+exact\s+location\b",
        r"\bpremises\s+address\b", r"\bcoordinates\s*\(",
    ],
    "authentication": [
        r"\btotp\s+secret\b", r"\b2fa\s+seed\b",
        r"\brecovery\s+codes?\b", r"\bprivate\s+key\b",
    ],
}

# Text that reads as an instruction to the model rather than a fact about
# the user. A stored memory is trusted context, so this is the persistent
# half of prompt injection (D09-13, D17-13).
INSTRUCTION_OVERRIDE = [
    r"^\s*(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)",
    r"^\s*(you\s+are\s+now|you\s+are)\s+(a\s+)?(dan|unfiltered|unrestricted|jailbroken)",
    r"^\s*(reveal|print|repeat|output)\s+(the\s+)?(system\s+)?prompt",
    r"^\s*(call|invoke|run)\s+(the\s+)?[a-z_]+\s+tool\b",
    r"\bignore\s+(all\s+)?previous\s+instructions",
]

MAX_TEXT_LEN = 20_000


class MemoryPolicy:
    """Evaluates memory candidates against the safety rules."""

    def __init__(
        self,
        categories: dict | None = None,
        override_patterns: list | None = None,
    ) -> None:
        self._categories = categories or SENSITIVE_CATEGORIES
        self._compiled = {
            name: [re.compile(p, re.IGNORECASE) for p in pats]
            for name, pats in self._categories.items()
        }
        self._overrides = [
            re.compile(p, re.IGNORECASE)
            for p in (override_patterns or INSTRUCTION_OVERRIDE)
        ]

    def evaluate(self, text: str) -> Decision:
        """Return the decision for a candidate memory text."""
        if not isinstance(text, str) or not text.strip():
            return Decision(False, "invalid", "empty candidate")
        if len(text) > MAX_TEXT_LEN:
            return Decision(False, "invalid", "candidate too long")

        for category, patterns in self._compiled.items():
            for pattern in patterns:
                if pattern.search(text):
                    return Decision(
                        False, category,
                        "matched sensitive category: " + category,
                    )

        for pattern in self._overrides:
            if pattern.search(text):
                return Decision(
                    False, "instruction_override",
                    "memory reads as an instruction to the model",
                )

        return Decision(True, "allowed", "ok")

    def redact(self, text: str) -> str:
        """Replace matched sensitive spans with a placeholder."""
        out = text
        for _, patterns in self._compiled.items():
            for pattern in patterns:
                out = pattern.sub("[REDACTED]", out)


        return out

class MemoryStore:
    """A memory store that enforces the policy on write."""

    def __init__(self, policy: MemoryPolicy | None = None) -> None:
        self._policy = policy or MemoryPolicy()
        self._items: list[str] = []
        self._rejected: list[tuple[str, Decision]] = []
        self._mu = threading.Lock()

    def write(self, text: str) -> Exception | None:
        d = self._policy.evaluate(text)
        if not d.allowed:
            self._rejected.append((text, d))
            return PermissionError("memory rejected: " + d.category)
        with self._mu:
            self._items.append(text)
        return None

    def items(self) -> list[str]:
        with self._mu:
            return list(self._items)

    def rejected_count(self) -> int:
        return len(self._rejected)

    def rejected_categories(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for _, d in self._rejected:
            out[d.category] = out.get(d.category, 0) + 1
        return out

    def clear(self) -> None:
        with self._mu:
            self._items.clear()
            self._rejected.clear()