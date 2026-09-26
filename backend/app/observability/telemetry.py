"""Telemetry collection and export."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    unit: str = ""


@dataclass
class TraceSpan:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    service: str
    start_time: datetime
    end_time: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    error: Optional[str] = None


class TelemetryCollector:
    def __init__(self, service_name: str = "astrovox-backend"):
        self.service_name = service_name
        self._metrics: List[MetricPoint] = []
        self._spans: List[TraceSpan] = []
        self._exporters: List[Callable[[List[MetricPoint], List[TraceSpan]], None]] = []

    def record_metric(self, metric: MetricPoint) -> None:
        self._metrics.append(metric)
        for exporter in self._exporters:
            try:
                exporter([metric], [])
            except Exception:
                logger.exception("metric exporter failed")

    def record_span(self, span: TraceSpan) -> None:
        self._spans.append(span)
        for exporter in self._exporters:
            try:
                exporter([], [span])
            except Exception:
                logger.exception("span exporter failed")

    def add_exporter(self, exporter: Callable[[List[MetricPoint], List[TraceSpan]], None]) -> None:
        self._exporters.append(exporter)

    def start_span(self, name: str, trace_id: str, parent_span_id: Optional[str] = None,
                   tags: Optional[Dict[str, str]] = None) -> TraceSpan:
        span = TraceSpan(
            trace_id=trace_id,
            span_id=self._generate_span_id(),
            parent_span_id=parent_span_id,
            name=name,
            service=self.service_name,
            start_time=datetime.now(timezone.utc),
            tags=tags or {},
        )
        self.record_span(span)
        return span

    def end_span(self, span: TraceSpan, status: str = "ok", error: Optional[str] = None) -> None:
        span.end_time = datetime.now(timezone.utc)
        span.status = status
        span.error = error
        self.record_span(span)

    @staticmethod
    def _generate_span_id() -> str:
        return f"{int(time.time() * 1e6):x}"


telemetry_collector = TelemetryCollector()
