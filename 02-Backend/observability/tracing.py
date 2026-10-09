import uuid
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any


@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000.0


class TraceContext:
    def __init__(self):
        self._local = threading.local()

    def get_current_span(self) -> Optional[Span]:
        return getattr(self._local, "current_span", None)

    def set_current_span(self, span: Optional[Span]):
        self._local.current_span = span

    def get_trace_id(self) -> Optional[str]:
        span = self.get_current_span()
        return span.trace_id if span else None


_trace_context = TraceContext()


def get_trace_context() -> TraceContext:
    return _trace_context


class Tracer:
    def __init__(self):
        self.spans: List[Span] = []
        self._lock = threading.Lock()

    def start_span(self, operation: str, parent_span: Optional[Span] = None, tags: Optional[Dict[str, Any]] = None) -> Span:
        trace_id = parent_span.trace_id if parent_span else str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        parent_span_id = parent_span.span_id if parent_span else None
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation=operation,
            start_time=time.perf_counter(),
            tags=tags or {},
        )
        with self._lock:
            self.spans.append(span)
        _trace_context.set_current_span(span)
        return span

    def end_span(self, span: Span):
        span.end_time = time.perf_counter()
        _trace_context.set_current_span(None)

    @contextmanager
    def span(self, operation: str, tags: Optional[Dict[str, Any]] = None):
        parent = _trace_context.get_current_span()
        span = self.start_span(operation, parent_span=parent, tags=tags)
        try:
            yield span
        finally:
            self.end_span(span)

    def get_trace(self, trace_id: str) -> List[Span]:
        return [s for s in self.spans if s.trace_id == trace_id]

    def export(self) -> Dict[str, Any]:
        return {
            "spans": [
                {
                    "span_id": s.span_id,
                    "trace_id": s.trace_id,
                    "parent_span_id": s.parent_span_id,
                    "operation": s.operation,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration_ms": s.duration_ms,
                    "tags": s.tags,
                }
                for s in self.spans
            ]
        }
