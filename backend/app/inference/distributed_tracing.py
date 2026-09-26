"""Distributed tracing for inference services."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation: str = ""
    service: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    duration_ms: Optional[float] = None

    def set_tag(self, key: str, value: Any) -> None:
        self.tags[key] = value

    def log(self, message: str, **kwargs: Any) -> None:
        self.logs.append({"timestamp": datetime.utcnow().isoformat(), "message": message, **kwargs})

    def finish(self, status: str = "ok") -> None:
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "service": self.service,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "status": self.status,
        }


class InferenceTracer:
    def __init__(self, service_name: str, exporter: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.service_name = service_name
        self.exporter = exporter
        self._spans: Dict[str, TraceSpan] = {}
        self._active_spans: Dict[str, TraceSpan] = {}

    def start_span(self, operation: str, parent_span_id: Optional[str] = None, trace_id: Optional[str] = None) -> TraceSpan:
        trace_id = trace_id or str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation=operation,
            service=self.service_name,
        )
        span.set_tag("service", self.service_name)
        self._spans[span_id] = span
        self._active_spans[span_id] = span
        return span

    def finish_span(self, span: TraceSpan, status: str = "ok") -> None:
        span.finish(status)
        self._active_spans.pop(span.span_id, None)
        if self.exporter:
            try:
                self.exporter(span.to_dict())
            except Exception:
                logger.exception("Failed to export span")

    def inject(self, headers: Dict[str, str], span: TraceSpan) -> None:
        headers["X-Trace-ID"] = span.trace_id
        headers["X-Span-ID"] = span.span_id
        if span.parent_span_id:
            headers["X-Parent-Span-ID"] = span.parent_span_id

    def extract(self, headers: Dict[str, str]) -> Optional[TraceSpan]:
        trace_id = headers.get("X-Trace-ID")
        span_id = headers.get("X-Span-ID")
        if not trace_id or not span_id:
            return None
        return self._spans.get(span_id)

    def trace_inference(self, operation: str, **kwargs: Any) -> "_InferenceTraceContext":
        return _InferenceTraceContext(tracer=self, operation=operation, **kwargs)


class _InferenceTraceContext:
    def __init__(self, tracer: InferenceTracer, operation: str, **kwargs: Any):
        self.tracer = tracer
        self.span = tracer.start_span(operation, **kwargs)
        self.span.set_tag("component", "inference")

    def __enter__(self) -> TraceSpan:
        return self.span

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        status = "error" if exc_type else "ok"
        self.tracer.finish_span(self.span, status)
