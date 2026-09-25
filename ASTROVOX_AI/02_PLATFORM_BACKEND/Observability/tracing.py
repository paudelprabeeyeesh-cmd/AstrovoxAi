"""Observability: distributed tracing."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"


class Tracer:
    def __init__(self) -> None:
        self._spans: List[Span] = []
        self._current_trace_id: Optional[str] = None

    @contextmanager
    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        span = Span(
            trace_id=self._current_trace_id or "trace",
            span_id=f"span_{len(self._spans)}",
            parent_span_id=None,
            name=name,
            attributes=attributes or {},
        )
        self._spans.append(span)
        try:
            yield span
        except Exception as exc:
            span.status = "error"
            raise
        finally:
            span.end_time = time.time()

    def get_spans(self) -> List[Dict[str, Any]]:
        return [
            {
                "trace_id": s.trace_id,
                "span_id": s.span_id,
                "parent_span_id": s.parent_span_id,
                "name": s.name,
                "duration_ms": (s.end_time or time.time()) - s.start_time,
                "status": s.status,
            }
            for s in self._spans
        ]


_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
