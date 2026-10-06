"""Observability utilities: metrics, tracing, and structured logging.

Provides lightweight, optional integrations for Prometheus metrics,
OpenTelemetry-style tracing, and structured JSON logging. These are
designed to be zero-dependency when the optional extras are not installed.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


_metrics: Dict[str, float] = {}
_traces: list = []
_logger = logging.getLogger("astrovox")


def incr(name: str, value: float = 1.0) -> None:
    _metrics[name] = _metrics.get(name, 0.0) + value


def timing(name: str, elapsed_ms: float) -> None:
    _metrics[f"{name}_ms"] = elapsed_ms


def gauge(name: str, value: float) -> None:
    _metrics[name] = value


def get_metrics() -> Dict[str, float]:
    return dict(_metrics)


def reset_metrics() -> None:
    _metrics.clear()


@dataclass
class Span:
    name: str
    start_ms: float
    end_ms: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        return max(0.0, self.end_ms - self.start_ms)


class Tracer:
    def __init__(self) -> None:
        self._spans: list[Span] = []

    def start(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Span:
        span = Span(name=name, start_ms=time.perf_counter() * 1000.0, attributes=attributes or {})
        self._spans.append(span)
        return span

    def end(self, span: Span) -> None:
        span.end_ms = time.perf_counter() * 1000.0

    def spans(self) -> list[Span]:
        return list(self._spans)


tracer = Tracer()


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    _logger.setLevel(level)


def log_event(event: str, payload: Optional[Dict[str, Any]] = None) -> None:
    record = {"event": event, "payload": payload or {}}
    _logger.info(json.dumps(record))
