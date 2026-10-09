from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from threat_intelligence.indicator_manager import Indicator, IndicatorManager


@dataclass(frozen=True)
class Match:
    value: str
    type: str
    indicator: Optional[Indicator]
    start: int
    end: int


_IP_RE = re.compile(r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)")
_DOMAIN_RE = re.compile(r"(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}")
_HASH_RE = re.compile(r"\b[0-9a-fA-F]{32}\b|\b[0-9a-fA-F]{40}\b|\b[0-9a-fA-F]{64}\b")


def _normalize_type(raw: str) -> str:
    lower = raw.lower()
    if lower == "ip" or lower == "ipv4":
        return "ip"
    if lower in ("domain", "host"):
        return "domain"
    if lower in ("hash", "md5", "sha1", "sha256"):
        return "hash"
    return lower


class IOCMatcher:
    def __init__(self, manager: IndicatorManager) -> None:
        self.manager = manager

    def _lookup(self, value: str, type_: str) -> Optional[Indicator]:
        return self.manager.get(type_, value)

    def match_text(self, text: str) -> List[Match]:
        matches: List[Match] = []
        for pattern, type_ in ((_IP_RE, "ip"), (_DOMAIN_RE, "domain"), (_HASH_RE, "hash")):
            for m in pattern.finditer(text):
                indicator = self._lookup(m.group(0), type_)
                matches.append(Match(m.group(0), type_, indicator, m.start(), m.end()))
        matches.sort(key=lambda m: (m.start, -len(m.value)))
        return _deduplicate(matches)

    def match_values(self, values: Sequence[str]) -> List[Match]:
        matches: List[Match] = []
        for value in values:
            if _IP_RE.fullmatch(value):
                type_ = "ip"
            elif _DOMAIN_RE.fullmatch(value):
                type_ = "domain"
            elif _HASH_RE.fullmatch(value):
                type_ = "hash"
            else:
                continue
            indicator = self._lookup(value, type_)
            matches.append(Match(value, type_, indicator, -1, -1))
        return matches

    def match_by_type(self, text: str, type_: str) -> List[Match]:
        patterns = {
            "ip": _IP_RE,
            "domain": _DOMAIN_RE,
            "hash": _HASH_RE,
        }
        pattern = patterns.get(_normalize_type(type_))
        if pattern is None:
            return []
        results: List[Match] = []
        for m in pattern.finditer(text):
            indicator = self._lookup(m.group(0), _normalize_type(type_))
            results.append(Match(m.group(0), _normalize_type(type_), indicator, m.start(), m.end()))
        return results

    def count_matches(self, text: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for m in self.match_text(text):
            counts[m.type] = counts.get(m.type, 0) + 1
        return counts


def _deduplicate(matches: List[Match]) -> List[Match]:
    seen: List[Match] = []
    used: List[Tuple[int, int]] = []
    for match in matches:
        overlap = any(not (match.end <= s or match.start >= e) for s, e in used)
        if not overlap:
            seen.append(match)
            used.append((match.start, match.end))
    return seen
