"""Massive observability: distributed traces, metrics, structured logs, SLOs, dependency map."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from . import make_id, now


@dataclass
class Trace:
    id: str
    name: str
    started_at: float = field(default_factory=now)
    ended_at: Optional[float] = None
    spans: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": round(((self.ended_at or now()) - self.started_at) * 1000, 2),
            "spans": self.spans,
            "attributes": self.attributes,
        }


class TraceStore:
    def __init__(self, history: int = 1000) -> None:
        self._traces: Deque[Trace] = deque(maxlen=history)

    def start(self, name: str, **attrs: Any) -> Trace:
        trace = Trace(id=make_id("trace"), name=name, attributes=dict(attrs))
        self._traces.append(trace)
        return trace

    def record_span(self, trace: Trace, span: Dict[str, Any]) -> None:
        trace.spans.append(span)

    def end(self, trace: Trace) -> None:
        trace.ended_at = now()

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in list(self._traces)[-limit:]]


@dataclass
class LogLine:
    timestamp: float
    level: str
    service: str
    message: str
    fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "service": self.service,
            "message": self.message,
            "fields": self.fields,
        }


class StructuredLogger:
    def __init__(self, history: int = 2000) -> None:
        self._history: Deque[LogLine] = deque(maxlen=history)
        self._listeners: List[Callable[[LogLine], None]] = []

    def log(self, level: str, service: str, message: str, **fields: Any) -> LogLine:
        line = LogLine(timestamp=now(), level=level, service=service, message=message, fields=fields)
        self._history.append(line)
        for listener in self._listeners:
            try:
                listener(line)
            except Exception:
                continue
        return line

    def info(self, service: str, message: str, **fields: Any) -> LogLine:
        return self.log("info", service, message, **fields)

    def warn(self, service: str, message: str, **fields: Any) -> LogLine:
        return self.log("warn", service, message, **fields)

    def error(self, service: str, message: str, **fields: Any) -> LogLine:
        return self.log("error", service, message, **fields)

    def search(self, *, level: Optional[str] = None, service: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for line in reversed(self._history):
            if level and line.level != level:
                continue
            if service and line.service != service:
                continue
            out.append(line.to_dict())
            if len(out) >= limit:
                break
        return out

    def subscribe(self, listener: Callable[[LogLine], None]) -> None:
        self._listeners.append(listener)


class DependencyMap:
    """Tracks service-to-service dependencies from observed calls."""

    def __init__(self) -> None:
        self._edges: Dict[Tuple[str, str], int] = defaultdict(int)
        self._services: set[str] = set()

    def record(self, source: str, target: str) -> None:
        self._services.add(source)
        self._services.add(target)
        self._edges[(source, target)] += 1

    def to_dict(self) -> Dict[str, Any]:
        nodes = [{"id": s} for s in sorted(self._services)]
        edges = [
            {"source": s, "target": t, "calls": c}
            for (s, t), c in sorted(self._edges.items())
        ]
        return {"nodes": nodes, "edges": edges, "services": len(self._services)}


@dataclass
class SLO:
    name: str
    target: float
    comparator: str = "lt"  # 'lt' or 'gt'
    window_s: float = 3600.0
    description: str = ""

    def is_breach(self, value: float) -> bool:
        if self.comparator == "lt":
            return value >= self.target
        return value <= self.target


class SLOTarget:
    def __init__(self, slo: SLO) -> None:
        self.slo = slo
        self._samples: Deque[Tuple[float, float]] = deque(maxlen=2000)  # (timestamp, value)

    def record(self, value: float) -> None:
        self._samples.append((now(), value))

    def compliance(self) -> Dict[str, Any]:
        relevant = [(t, v) for t, v in self._samples if now() - t <= self.slo.window_s]
        if not relevant:
            return {"name": self.slo.name, "samples": 0, "compliance": 1.0, "target": self.slo.target}
        breaches = sum(1 for _, v in relevant if self.slo.is_breach(v))
        return {
            "name": self.slo.name,
            "samples": len(relevant),
            "breaches": breaches,
            "compliance": round(1.0 - breaches / len(relevant), 4),
            "target": self.slo.target,
            "comparator": self.slo.comparator,
        }


class Observability:
    def __init__(self) -> None:
        self.traces = TraceStore()
        self.logs = StructuredLogger()
        self.dependencies = DependencyMap()
        self._slos: Dict[str, SLOTarget] = {}
        # Default SLOs
        self.define(SLO("latency_p95_ms", 8000.0, "lt"))
        self.define(SLO("error_rate", 0.05, "lt"))
        self.define(SLO("retrieval_precision", 0.7, "gt"))
        self.define(SLO("availability", 0.99, "gt"))

    def define(self, slo: SLO) -> None:
        self._slos[slo.name] = SLOTarget(slo)

    def record_slo(self, name: str, value: float) -> None:
        target = self._slos.get(name)
        if target:
            target.record(value)

    def slo_status(self) -> List[Dict[str, Any]]:
        return [t.compliance() for t in self._slos.values()]

    def status(self) -> Dict[str, Any]:
        return {
            "traces": self.traces.recent(limit=10),
            "logs": self.logs.search(limit=20),
            "dependencies": self.dependencies.to_dict(),
            "slos": self.slo_status(),
        }


_GLOBAL_OBS: Optional[Observability] = None


def get_aios_observability() -> Observability:
    global _GLOBAL_OBS
    if _GLOBAL_OBS is None:
        _GLOBAL_OBS = Observability()
    return _GLOBAL_OBS