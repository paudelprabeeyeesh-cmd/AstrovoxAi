"""Distributed tracing context propagation."""
from __future__ import annotations

import threading
import time
import uuid
from typing import Dict, Optional


class TraceContext:
    def __init__(self, trace_id: str, span_id: str, sampled: bool = True):
        self.trace_id = trace_id
        self.span_id = span_id
        self.sampled = sampled

    def to_headers(self) -> Dict[str, str]:
        return {
            "x-trace-id": self.trace_id,
            "x-span-id": self.span_id,
            "x-sampled": "1" if self.sampled else "0",
        }

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Optional["TraceContext"]:
        trace_id = headers.get("x-trace-id")
        span_id = headers.get("x-span-id")
        if not trace_id or not span_id:
            return None
        sampled = headers.get("x-sampled", "1") == "1"
        return cls(trace_id=trace_id, span_id=span_id, sampled=sampled)


class DistributedTracer:
    def __init__(self) -> None:
        self._local = threading.local()

    def start_trace(self, name: str, sampled: bool = True) -> TraceContext:
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        ctx = TraceContext(trace_id=trace_id, span_id=span_id, sampled=sampled)
        self._local.current = ctx
        return ctx

    def get_current_context(self) -> Optional[TraceContext]:
        return getattr(self._local, "current", None)

    def start_span(self, name: str) -> TraceContext:
        parent = self.get_current_context()
        span_id = uuid.uuid4().hex[:16]
        ctx = TraceContext(
            trace_id=parent.trace_id if parent else uuid.uuid4().hex,
            span_id=span_id,
            sampled=parent.sampled if parent else True,
        )
        self._local.current = ctx
        return ctx

    def end_span(self) -> None:
        parent = getattr(self._local, "_parent", None)
        self._local.current = parent

    def inject(self, context: TraceContext) -> Dict[str, str]:
        return context.to_headers()

    def extract(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        return TraceContext.from_headers(headers)


distributed_tracer = DistributedTracer()
