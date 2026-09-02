"""Observability: traces, metrics, SLO tracking."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional


@dataclass
class Span:
    id: str
    name: str
    started_at: float
    ended_at: Optional[float] = None
    parent_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        duration = (self.ended_at or time.time()) - self.started_at
        return {
            "id": self.id,
            "name": self.name,
            "duration_ms": round(duration * 1000, 2),
            "parent_id": self.parent_id,
            "attributes": self.attributes,
            "status": self.status,
            "error": self.error,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


class Tracer:
    def __init__(self) -> None:
        self._spans: Deque[Span] = deque(maxlen=2000)
        self._active: Dict[str, Span] = {}

    def start(self, name: str, **attributes: Any) -> Span:
        span = Span(
            id=f"sp_{uuid.uuid4().hex[:10]}",
            name=name,
            started_at=time.time(),
            attributes=dict(attributes),
        )
        self._active[span.id] = span
        return span

    def end(self, span: Span, *, status: str = "ok", error: Optional[str] = None) -> None:
        span.ended_at = time.time()
        span.status = status
        span.error = error
        self._spans.append(span)
        self._active.pop(span.id, None)

    def recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in list(self._spans)[-limit:]]

    def for_request(self, request_id: str) -> List[Dict[str, Any]]:
        return [
            s.to_dict()
            for s in self._spans
            if s.attributes.get("request_id") == request_id
        ]


@dataclass
class SLODefinition:
    name: str
    threshold: float
    comparator: str  # 'lt' (less than) or 'gt'
    description: str = ""


class SLOTracker:
    def __init__(self) -> None:
        self._slos: Dict[str, SLODefinition] = {}
        self._samples: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=200))
        self._breaches: Dict[str, int] = defaultdict(int)

    def define(self, slo: SLODefinition) -> None:
        self._slos[slo.name] = slo

    def record(self, name: str, value: float) -> bool:
        slo = self._slos.get(name)
        if not slo:
            return True
        self._samples[name].append(value)
        ok = (value < slo.threshold) if slo.comparator == "lt" else (value > slo.threshold)
        if not ok:
            self._breaches[name] += 1
        return ok

    def compliance(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name, slo in self._slos.items():
            samples = list(self._samples.get(name, []))
            if not samples:
                out[name] = {"breaches": 0, "compliance": 1.0, "samples": 0}
                continue
            breaches = sum(
                1
                for v in samples
                if (v >= slo.threshold) if slo.comparator == "lt" else (v <= slo.threshold)
            )
            out[name] = {
                "breaches": breaches,
                "compliance": round(1.0 - breaches / len(samples), 4),
                "samples": len(samples),
            }
        return out


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=500))
        self._lock_proxy: List[Any] = []

    def inc(self, name: str, value: float = 1.0) -> None:
        self._counters[name] += value

    def gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        self._histograms[name].append(value)

    def snapshot(self) -> Dict[str, Any]:
        histograms: Dict[str, Any] = {}
        for name, samples in self._histograms.items():
            if not samples:
                continue
            sorted_samples = sorted(samples)
            n = len(sorted_samples)
            histograms[name] = {
                "count": n,
                "avg": round(sum(sorted_samples) / n, 4),
                "p50": round(sorted_samples[n // 2], 4),
                "p95": round(sorted_samples[min(n - 1, int(n * 0.95))], 4),
            }
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": histograms,
        }


class Observability:
    def __init__(self) -> None:
        self.tracer = Tracer()
        self.metrics = MetricsRegistry()
        self.slos = SLOTracker()
        # Default SLOs
        self.slos.define(SLODefinition("latency_p95_ms", 8000.0, "lt"))
        self.slos.define(SLODefinition("error_rate", 0.05, "lt"))
        self.slos.define(SLODefinition("retrieval_precision", 0.7, "gt"))


_GLOBAL_OBS: Optional[Observability] = None


def get_observability() -> Observability:
    global _GLOBAL_OBS
    if _GLOBAL_OBS is None:
        _GLOBAL_OBS = Observability()
    return _GLOBAL_OBS