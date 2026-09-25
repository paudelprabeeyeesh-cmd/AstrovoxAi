"""Distributed tracing with OpenTelemetry."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SpanKind(str, Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(str, Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanAttribute:
    key: str
    value: Any


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind = SpanKind.INTERNAL
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: List[SpanAttribute] = field(default_factory=list)
    status: SpanStatus = SpanStatus.UNSET
    events: List[Dict[str, Any]] = field(default_factory=list)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes.append(SpanAttribute(key=key, value=value))

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({"name": name, "attributes": attributes or {}, "timestamp": time.time()})

    def end(self) -> None:
        self.end_time = time.time()

    def is_recording(self) -> bool:
        return self.end_time is None


@dataclass
class Trace:
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    root_span_id: Optional[str] = None

    def add_span(self, span: Span) -> None:
        self.spans.append(span)
        if self.root_span_id is None:
            self.root_span_id = span.span_id

    def get_duration_ms(self) -> float:
        if not self.spans:
            return 0.0
        root = next((s for s in self.spans if s.span_id == self.root_span_id), None)
        if root and root.end_time:
            return (root.end_time - root.start_time) * 1000
        return 0.0


class OpenTelemetryTracer:
    """OpenTelemetry-compatible tracer."""

    def __init__(self, service_name: str, otlp_endpoint: Optional[str] = None) -> None:
        self._service_name = service_name
        self._otlp_endpoint = otlp_endpoint
        self._traces: Dict[str, Trace] = {}
        self._span_stack: List[Span] = []
        self._lock = asyncio.Lock() if _HAS_ASYNCIO else None
        self._initialized = False
        self._exporters: List[Any] = []

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        if self._otlp_endpoint:
            self._exporters.append(OTLPExporter(self._otlp_endpoint))
        logger.info("OpenTelemetry tracer initialized for %s", self._service_name)

    def start_trace(self, trace_id: str, root_span_name: str) -> Span:
        span = Span(
            trace_id=trace_id,
            span_id=_generate_span_id(),
            parent_span_id=None,
            name=root_span_name,
            kind=SpanKind.SERVER,
        )
        if trace_id not in self._traces:
            self._traces[trace_id] = Trace(trace_id=trace_id)
        self._traces[trace_id].add_span(span)
        self._span_stack.append(span)
        logger.debug("Started trace %s, span %s", trace_id, span.span_id)
        return span

    def start_span(
        self,
        trace_id: str,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
    ) -> Span:
        parent = self._span_stack[-1] if self._span_stack else None
        span = Span(
            trace_id=trace_id,
            span_id=_generate_span_id(),
            parent_span_id=parent.span_id if parent else None,
            name=name,
            kind=kind,
        )
        if trace_id in self._traces:
            self._traces[trace_id].add_span(span)
        self._span_stack.append(span)
        return span

    def end_span(self, span: Span) -> None:
        if self._span_stack and self._span_stack[-1].span_id == span.span_id:
            self._span_stack.pop()
        span.end()
        logger.debug("Ended span %s", span.span_id)

    def record_exception(self, span: Span, exc: BaseException) -> None:
        span.status = SpanStatus.ERROR
        span.add_event("exception", {
            "exception.type": type(exc).__name__,
            "exception.message": str(exc),
            "stack": _get_stack_info(exc),
        })

    async def shutdown(self) -> None:
        for exporter in self._exporters:
            await asyncio.gather(*[e.flush() for e in self._exporters], return_exceptions=True)
        self._initialized = False

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        return self._traces.get(trace_id)

    def get_all_traces(self) -> List[Trace]:
        return list(self._traces.values())


class OTLPExporter:
    """Export traces to OTLP endpoint."""

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint

    async def export(self, spans: List[Span]) -> None:
        payload = _serialize_spans(spans)
        await _post_otlp(self._endpoint, payload)

    async def flush(self) -> None:
        pass


def _generate_span_id() -> str:
    return f"{time.time_ns():x}{__import__('random').getrandbits(32):08x}"[:16]


def _generate_trace_id() -> str:
    return f"{time.time_ns():x}{__import__('random').getrandbits(64):016x}"[:32]


def _get_stack_info(exc: BaseException) -> str:
    import traceback
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def _serialize_spans(spans: List[Span]) -> Dict[str, Any]:
    return {
        "resource_spans": [{
            "resource": {"attributes": [{"key": "service.name", "value": {"string_value": "astrovoxai"}}]},
            "scope_spans": [{
                "spans": [
                    {
                        "trace_id": s.trace_id,
                        "span_id": s.span_id,
                        "name": s.name,
                        "kind": s.kind.value,
                        "start_time_unix_nano": int(s.start_time * 1e9),
                        "end_time_unix_nano": int((s.end_time or s.start_time) * 1e9),
                        "status": {"code": 1 if s.status == SpanStatus.ERROR else 2},
                    }
                    for s in spans
                ]
            }]
        }]
    }


async def _post_otlp(endpoint: str, payload: Dict[str, Any]) -> None:
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload, headers={"Content-Type": "application/json"}) as resp:
                if resp.status != 200:
                    logger.warning("OTLP export failed: %s %s", resp.status, await resp.text())
    except Exception as exc:
        logger.warning("OTLP export error: %s", exc)


_tracer: Optional[OpenTelemetryTracer] = None


def get_tracer(
    service_name: str = "astrovoxai",
    otlp_endpoint: Optional[str] = None,
) -> OpenTelemetryTracer:
    global _tracer
    if _tracer is None:
        _tracer = OpenTelemetryTracer(service_name=service_name, otlp_endpoint=otlp_endpoint)
        if _HAS_ASYNCIO:
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_tracer.initialize())
            loop.close()
    return _tracer


try:
    import asyncio
    _HAS_ASYNCIO = True
except ImportError:
    _HAS_ASYNCIO = False
