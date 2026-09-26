"""Distributed tracing with correlation IDs."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid


class SpanKind(Enum):
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    INTERNAL = "internal"


class SpanStatus(Enum):
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Trace:
    trace_id: str
    spans: List[Span]
    root_span: Optional[Span] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class TracingManager:
    _traces: Dict[str, Trace] = {}
    _spans: Dict[str, Span] = {}

    @classmethod
    def generate_trace_id(cls) -> str:
        return uuid.uuid4().hex

    @classmethod
    def generate_span_id(cls) -> str:
        return uuid.uuid4().hex[:16]

    @classmethod
    def start_span(cls, name: str, kind: SpanKind = SpanKind.INTERNAL,
                   parent_span_id: Optional[str] = None,
                   trace_id: Optional[str] = None,
                   attributes: Optional[Dict[str, Any]] = None) -> Span:
        trace_id = trace_id or cls.generate_trace_id()
        span_id = cls.generate_span_id()
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            start_time=datetime.now(timezone.utc),
            attributes=attributes or {}
        )
        cls._spans[span_id] = span

        if trace_id not in cls._traces:
            cls._traces[trace_id] = Trace(trace_id=trace_id, spans=[])
        cls._traces[trace_id].spans.append(span)
        return span

    @classmethod
    def end_span(cls, span_id: str, status: SpanStatus = SpanStatus.OK,
                 attributes: Optional[Dict[str, Any]] = None) -> Optional[Span]:
        span = cls._spans.get(span_id)
        if not span:
            return None
        span.end_time = datetime.now(timezone.utc)
        span.status = status
        if attributes:
            span.attributes.update(attributes)
        return span

    @classmethod
    def add_event(cls, span_id: str, name: str, attributes: Optional[Dict[str, Any]] = None) -> Optional[Span]:
        span = cls._spans.get(span_id)
        if not span:
            return None
        span.events.append({
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": attributes or {}
        })
        return span

    @classmethod
    def get_trace(cls, trace_id: str) -> Optional[Trace]:
        return cls._traces.get(trace_id)

    @classmethod
    def get_span(cls, span_id: str) -> Optional[Span]:
        return cls._spans.get(span_id)

    @classmethod
    def get_trace_duration(cls, trace_id: str) -> Optional[float]:
        trace = cls._traces.get(trace_id)
        if not trace or not trace.spans:
            return None
        root = trace.spans[0]
        if root.end_time and root.start_time:
            return (root.end_time - root.start_time).total_seconds()
        return None

    @classmethod
    def export_trace(cls, trace_id: str) -> Dict[str, Any]:
        trace = cls._traces.get(trace_id)
        if not trace:
            return {}
        return {
            "trace_id": trace_id,
            "spans": [
                {
                    "span_id": s.span_id,
                    "parent_span_id": s.parent_span_id,
                    "name": s.name,
                    "kind": s.kind.value,
                    "status": s.status.value,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "attributes": s.attributes,
                    "duration_ms": ((s.end_time - s.start_time).total_seconds() * 1000) if s.end_time and s.start_time else 0
                }
                for s in trace.spans
            ]
        }
