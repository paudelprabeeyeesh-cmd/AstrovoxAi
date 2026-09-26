"""Distributed tracing for inference request lifecycle."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation: str
    service: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    duration_ms: Optional[float] = None


class InferenceTracer:
    def __init__(self, service_name: str, collector_url: Optional[str] = None, sample_rate: float = 1.0):
        self.service_name = service_name
        self.collector_url = collector_url
        self.sample_rate = sample_rate
        self._spans: Dict[str, TraceSpan] = {}
        self._active_spans: Dict[str, TraceSpan] = {}
        self._lock = threading.RLock()

    def start_span(self, trace_id: str, span_id: str, parent_span_id: Optional[str] = None, operation: str = "") -> TraceSpan:
        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation=operation,
            service=self.service_name,
        )
        with self._lock:
            self._spans[span_id] = span
            self._active_spans[span_id] = span
        logger.debug("Started span %s for operation %s", span_id, operation)
        return span

    def finish_span(self, span_id: str, status: str = "ok") -> None:
        with self._lock:
            span = self._active_spans.pop(span_id, None)
            if not span:
                return
            span.end_time = datetime.utcnow()
            span.status = status
            span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
            logger.debug("Finished span %s in %.2fms", span_id, span.duration_ms)

    def add_tag(self, span_id: str, key: str, value: Any) -> None:
        with self._lock:
            span = self._spans.get(span_id)
            if span:
                span.tags[key] = value

    def log_event(self, span_id: str, event: str, **kwargs: Any) -> None:
        with self._lock:
            span = self._spans.get(span_id)
            if span:
                span.logs.append({"timestamp": datetime.utcnow().isoformat(), "event": event, **kwargs})

    def inject_context(self, headers: Dict[str, str], span: TraceSpan) -> None:
        headers["X-Trace-ID"] = span.trace_id
        headers["X-Span-ID"] = span.span_id

    def extract_context(self, headers: Dict[str, str]) -> Optional[TraceSpan]:
        trace_id = headers.get("X-Trace-ID")
        span_id = headers.get("X-Span-ID")
        if trace_id and span_id:
            with self._lock:
                return self._spans.get(span_id)
        return None

    def export_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._span_to_dict(s) for s in self._spans.values() if s.trace_id == trace_id]

    def _span_to_dict(self, span: TraceSpan) -> Dict[str, Any]:
        return {
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "operation": span.operation,
            "service": span.service,
            "start_time": span.start_time.isoformat(),
            "end_time": span.end_time.isoformat() if span.end_time else None,
            "duration_ms": span.duration_ms,
            "tags": span.tags,
            "status": span.status,
            "logs": span.logs,
        }

    def get_trace_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "service": self.service_name,
                "total_spans": len(self._spans),
                "active_spans": len(self._active_spans),
                "spans": [self._span_to_dict(s) for s in self._spans.values()],
            }
