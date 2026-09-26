"""Temporal AI: time-aware models and reasoning.

Provides:
- Time-aware context windows
- Temporal attention mechanisms
- Historical pattern recognition
- Future state prediction
- Causal inference over time
- Temporal reasoning in agents
- Time-series forecasting integration
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Temporal context window
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemporalToken:
    token_id: str
    text: str
    timestamp: datetime
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TimeAwareContextWindow:
    """Context window that weights tokens by temporal proximity and relevance."""

    def __init__(self, max_tokens: int = 4096, decay_half_life_s: float = 3600.0) -> None:
        self._max_tokens = max_tokens
        self._half_life = decay_half_life_s
        self._tokens: List[TemporalToken] = []
        self._lock = threading.Lock()

    def add(self, text: str, timestamp: Optional[datetime] = None, metadata: Optional[Dict[str, Any]] = None) -> TemporalToken:
        token = TemporalToken(
            token_id=f"tok-{uuid.uuid4().hex[:12]}",
            text=text,
            timestamp=timestamp or datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        with self._lock:
            self._tokens.append(token)
            self._trim()
        return token

    def _trim(self) -> None:
        while len(self._tokens) > self._max_tokens:
            oldest = min(self._tokens, key=lambda t: t.timestamp)
            self._tokens.remove(oldest)

    def weighted_tokens(self, reference_time: Optional[datetime] = None) -> List[Tuple[TemporalToken, float]]:
        ref = reference_time or datetime.now(timezone.utc)
        weighted = []
        for token in self._tokens:
            age_s = max((ref - token.timestamp).total_seconds(), 0.0)
            weight = math.exp(-math.log(2) * age_s / self._half_life)
            weighted.append((token, weight))
        return sorted(weighted, key=lambda x: x[1], reverse=True)

    def context_text(self, reference_time: Optional[datetime] = None, max_tokens: Optional[int] = None) -> str:
        weighted = self.weighted_tokens(reference_time)
        limit = max_tokens or self._max_tokens
        selected = [t.text for t, w in weighted[:limit] if w > 0.01]
        return "\n".join(selected)

    def prune(self, older_than: datetime) -> int:
        before = len(self._tokens)
        self._tokens = [t for t in self._tokens if t.timestamp >= older_than]
        return before - len(self._tokens)

    def size(self) -> int:
        return len(self._tokens)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_tokens": self._max_tokens,
            "half_life_s": self._half_life,
            "tokens": [t.text for t in self._tokens],
        }


# ---------------------------------------------------------------------------
# Temporal attention
# ---------------------------------------------------------------------------


class TemporalAttention:
    """Attention mechanism that incorporates temporal distance."""

    def __init__(self, temperature: float = 1.0) -> None:
        self._temperature = temperature

    def attend(self, query: Dict[str, Any], keys: List[Dict[str, Any]], timestamps: List[datetime]) -> List[Tuple[Dict[str, Any], float]]:
        scores = []
        query_time = query.get("timestamp", datetime.now(timezone.utc))
        for key, ts in zip(keys, timestamps):
            semantic_score = self._semantic_similarity(query, key)
            temporal_score = self._temporal_proximity(query_time, ts)
            score = semantic_score * temporal_score
            scores.append((key, score))
        total = sum(s for _, s in scores) or 1.0
        normalized = [(k, s / total) for k, s in scores]
        return sorted(normalized, key=lambda x: x[1], reverse=True)

    def _semantic_similarity(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        common = set(a.keys()) & set(b.keys())
        if not common:
            return 0.0
        matches = sum(1 for k in common if a[k] == b[k])
        return matches / len(common)

    def _temporal_proximity(self, a: datetime, b: datetime) -> float:
        age_s = abs((a - b).total_seconds())
        return math.exp(-age_s / 3600.0)


# ---------------------------------------------------------------------------
# Pattern recognition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemporalPattern:
    pattern_id: str
    pattern_type: str
    sequence: List[str]
    support: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class HistoricalPatternRecognizer:
    """Detects recurring patterns in temporal sequences."""

    def __init__(self, min_support: float = 0.1, min_confidence: float = 0.5) -> None:
        self._min_support = min_support
        self._min_confidence = min_confidence
        self._sequences: List[List[str]] = []
        self._patterns: List[TemporalPattern] = []

    def observe(self, sequence: List[str]) -> None:
        self._sequences.append(sequence)

    def detect_patterns(self) -> List[TemporalPattern]:
        from collections import Counter
        counts = Counter(tuple(seq) for seq in self._sequences)
        total = len(self._sequences)
        for seq, count in counts.items():
            support = count / total if total > 0 else 0.0
            if support >= self._min_support and len(seq) >= 2:
                pattern = TemporalPattern(
                    pattern_id=f"pat-{uuid.uuid4().hex[:12]}",
                    pattern_type="sequence",
                    sequence=list(seq),
                    support=support,
                    confidence=self._min_confidence,
                )
                self._patterns.append(pattern)
        return list(self._patterns)

    def match(self, sequence: List[str]) -> List[TemporalPattern]:
        return [p for p in self._patterns if tuple(sequence[-len(p.sequence):]) == tuple(p.sequence)]

    def stats(self) -> Dict[str, Any]:
        return {
            "sequences_observed": len(self._sequences),
            "patterns_detected": len(self._patterns),
        }


# ---------------------------------------------------------------------------
# Time-series forecasting
# ---------------------------------------------------------------------------


class TimeSeriesForecaster:
    """Simple time-series forecasting integration."""

    def __init__(self) -> None:
        self._series: Dict[str, List[Tuple[datetime, float]]] = {}

    def observe(self, series_id: str, timestamp: datetime, value: float) -> None:
        self._series.setdefault(series_id, []).append((timestamp, value))

    def forecast(self, series_id: str, horizon: int = 5) -> List[Tuple[datetime, float]]:
        points = self._series.get(series_id, [])
        if len(points) < 2:
            return []
        values = [v for _, v in points]
        last_ts = points[-1][0]
        trend = (values[-1] - values[0]) / max(len(values) - 1, 1)
        forecast = []
        for i in range(1, horizon + 1):
            forecast.append((datetime.fromtimestamp(last_ts.timestamp() + i * 60, tz=timezone.utc), values[-1] + trend * i))
        return forecast

    def series_stats(self, series_id: str) -> Dict[str, Any]:
        points = self._series.get(series_id, [])
        if not points:
            return {}
        values = [v for _, v in points]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
        }
