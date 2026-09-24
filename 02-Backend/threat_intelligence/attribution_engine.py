from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from threat_intelligence.indicator_manager import Indicator, IndicatorManager
from threat_intelligence.ioc_matcher import Match, IOCMatcher


@dataclass
class AttributionCandidate:
    actor: str
    score: float = 0.0
    matched_indicators: List[Indicator] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.actor:
            raise ValueError("Actor name must not be empty")
        if not (0.0 <= self.score <= 100.0):
            raise ValueError("Score must be between 0 and 100")


class AttributionEngine:
    def __init__(self, manager: IndicatorManager) -> None:
        self.manager = manager
        self._attributions: Dict[str, AttributionCandidate] = {}

    def register(self, actor: str) -> None:
        if actor not in self._attributions:
            self._attributions[actor] = AttributionCandidate(actor=actor)

    def link_indicator(self, actor: str, indicator: Indicator) -> None:
        self.register(actor)
        candidate = self._attributions[actor]
        if indicator not in candidate.matched_indicators:
            candidate.matched_indicators.append(indicator)
        candidate.score = min(100.0, candidate.score + indicator.confidence * 10.0)
        candidate.last_updated = datetime.utcnow()

    def score_from_matches(self, actor: str, matches: Iterable[Match]) -> None:
        self.register(actor)
        candidate = self._attributions[actor]
        added = 0.0
        count = 0
        for match in matches:
            if match.indicator is not None:
                added += match.indicator.confidence * 10.0
                count += 1
                if match.indicator not in candidate.matched_indicators:
                    candidate.matched_indicators.append(match.indicator)
        candidate.score = min(100.0, candidate.score + added)
        if count:
            candidate.last_updated = datetime.utcnow()

    def get(self, actor: str) -> Optional[AttributionCandidate]:
        return self._attributions.get(actor)

    def ranked(self) -> List[AttributionCandidate]:
        return sorted(self._attributions.values(), key=lambda c: (-c.score, c.actor))

    def prune_below(self, threshold: float) -> List[str]:
        removed = [actor for actor, c in self._attributions.items() if c.score < threshold]
        for actor in removed:
            del self._attributions[actor]
        return removed

    def __len__(self) -> int:
        return len(self._attributions)
