import re
from dataclasses import dataclass
from typing import List


@dataclass
class ScrubResult:
    original: str
    sanitized: str
    blocked: bool
    matched_rules: List[str]


class CommandScrubber:
    DANGEROUS_PATTERNS = [
        re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
        re.compile(r"\bchmod\s+777\b", re.IGNORECASE),
        re.compile(r"\bdd\s+if=\S+\s+of=\S+", re.IGNORECASE),
        re.compile(r">\s*/dev/sd[a-z]", re.IGNORECASE),
        re.compile(r"\bmkfs\b", re.IGNORECASE),
        re.compile(r"\bcurl\s+.*\|\s*(bash|sh)\b", re.IGNORECASE),
    ]

    @classmethod
    def scan(cls, command: str) -> ScrubResult:
        matched = [p.pattern for p in cls.DANGEROUS_PATTERNS if p.search(command)]
        if matched:
            return ScrubResult(
                original=command,
                sanitized="",
                blocked=True,
                matched_rules=matched,
            )
        return ScrubResult(
            original=command,
            sanitized=command.strip(),
            blocked=False,
            matched_rules=[],
        )
