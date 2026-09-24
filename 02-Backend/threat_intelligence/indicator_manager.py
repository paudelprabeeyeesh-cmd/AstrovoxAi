from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional


@dataclass
class Indicator:
    value: str
    type: str
    confidence: float = 1.0
    source: Optional[str] = None
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Indicator value must not be empty")
        if not self.type:
            raise ValueError("Indicator type must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0 and 1")


class IndicatorManager:
    def __init__(self) -> None:
        self._indicators: Dict[str, Indicator] = {}

    def add(self, indicator: Indicator) -> None:
        key = (indicator.type.lower(), indicator.value.lower())
        if key in self._indicators:
            existing = self._indicators[key]
            existing.confidence = max(existing.confidence, indicator.confidence)
            existing.last_seen = max(existing.last_seen, indicator.last_seen)
            existing.tags = sorted(set(existing.tags + indicator.tags))
            if indicator.source:
                existing.source = indicator.source
        else:
            self._indicators[key] = indicator

    def remove(self, type_: str, value: str) -> None:
        key = (type_.lower(), value.lower())
        self._indicators.pop(key, None)

    def get(self, type_: str, value: str) -> Optional[Indicator]:
        key = (type_.lower(), value.lower())
        return self._indicators.get(key)

    def list_all(self) -> List[Indicator]:
        return sorted(self._indicators.values(), key=lambda i: (i.type, i.value))

    def filter_by_type(self, type_: str) -> List[Indicator]:
        return [i for i in self._indicators.values() if i.type.lower() == type_.lower()]

    def filter_by_tag(self, tag: str) -> List[Indicator]:
        return [i for i in self._indicators.values() if tag in i.tags]

    def filter_by_confidence(self, threshold: float) -> List[Indicator]:
        return [i for i in self._indicators.values() if i.confidence >= threshold]

    def __len__(self) -> int:
        return len(self._indicators)
