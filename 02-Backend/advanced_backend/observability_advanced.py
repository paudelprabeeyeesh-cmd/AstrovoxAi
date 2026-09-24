import json
import logging
import time
import threading
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
span_stack: List["Span"] = []


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    start_time: float = field(default_factory=time.time)
    attributes: Dict[str, Any] = field(default_factory=dict)
    end_time: Optional[float] = None

    def end(self) -> None:
        self.end_time = time.time()


@dataclass
class MetricSample:
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: float = field(default_factory=time.time)


class ObservableRegistry:
    def __init__(self) -> None:
        self._metrics: Dict[str, List[MetricSample]] = defaultdict(list)
        self._logs: List[Dict[str, Any]] = []
        self._spans: Dict[str, List[Span]] = defaultdict(list)
        self._lock = threading.Lock()

    def record(self, sample: MetricSample) -> None:
        with self._lock:
            self._metrics[sample.name].append(sample)
            self._logs.append(
                {
                    "level": "info",
                    "event": "metric",
                    "name": sample.name,
                    "value": sample.value,
                    "timestamp": sample.timestamp,
                }
            )

    def log(self, level: str, message: str, **ctx: Any) -> None:
        entry = {
            "level": level,
            "message": message,
            "timestamp": time.time(),
            "request_id": _request_id.get(),
            **ctx,
        }
        with self._lock:
            self._logs.append(entry)

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Span:
        trace_id = _request_id.get() or __import__("uuid").uuid4().hex
        parent_id = span_stack[-1].span_id if span_stack else None
        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=__import__("uuid").uuid4().hex,
            parent_id=parent_id,
            attributes=attributes or {},
        )
        span_stack.append(span)
        return span

    def end_span(self, span: Span) -> None:
        span.end()
        if span in span_stack:
            span_stack.remove(span)
        with self._lock:
            self._spans[span.trace_id].append(span)
            self._logs.append(
                {
                    "level": "info",
                    "event": "span",
                    "span_id": span.span_id,
                    "duration_ms": (span.end_time - span.start_time) * 1000,
                    "timestamp": span.end_time,
                }
            )

    def export(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "metrics": {k: [{"value": s.value, "labels": s.labels, "ts": s.timestamp} for s in v] for k, v in self._metrics.items()},
                "logs": list(self._logs),
                "spans": {k: [{"name": s.name, "duration_ms": (s.end_time or s.start_time) - s.start_time} for s in v] for k, v in self._spans.items()},
            }


observability = ObservableRegistry()
