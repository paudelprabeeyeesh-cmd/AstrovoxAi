"""Observability helpers: structured logging, request tracing, and correlation IDs."""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional

try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


_correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    return _correlation_id_var.get()


def set_correlation_id(value: Optional[str]) -> None:
    _correlation_id_var.set(value)


def new_correlation_id() -> str:
    cid = str(uuid.uuid4())
    set_correlation_id(cid)
    return cid


def _configure_structlog():
    if not STRUCTLOG_AVAILABLE:
        return None
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()


_structured_logger = _configure_structlog()


def get_logger(name: str = "astravox") -> logging.Logger:
    if STRUCTLOG_AVAILABLE and _structured_logger is not None:
        return structlog.get_logger(name)
    return logging.getLogger(name)


def log_event(logger, event: str, level: str = "info", **kwargs):
    kwargs.setdefault("correlation_id", get_correlation_id())
    if STRUCTLOG_AVAILABLE and hasattr(logger, event):
        fn = getattr(logger, level, logger.info)
        fn(event, **kwargs)
    else:
        log_fn = getattr(logger, level, logger.info)
        log_fn(f"{event} | {kwargs}")


class Span:
    _SPAN_COUNTER = 0

    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger or get_logger()
        self.start: float = 0.0
        self.span_id: str = ""
        self.trace_id: str = ""

    def __enter__(self):
        Span._SPAN_COUNTER += 1
        self.span_id = f"span-{Span._SPAN_COUNTER}"
        self.trace_id = get_correlation_id() or str(uuid.uuid4())
        set_correlation_id(self.trace_id)
        self.start = time.time()
        log_event(
            self.logger,
            "span_start",
            level="debug",
            span_id=self.span_id,
            trace_id=self.trace_id,
            operation=self.name,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start) * 1000
        log_event(
            self.logger,
            "span_end",
            level="debug",
            span_id=self.span_id,
            trace_id=self.trace_id,
            operation=self.name,
            duration_ms=round(duration_ms, 3),
            status="error" if exc_type else "ok",
        )
        return False


def observe(name: str, **kwargs):
    return Span(name=name, **kwargs)


class RequestLogger:
    def __init__(self, logger=None):
        self.logger = logger or get_logger("astravox.request")

    def log_request(self, request, response, duration: float, **extra):
        log_event(
            self.logger,
            "http_request",
            level="info",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 3),
            client=getattr(request, "client", None),
            **extra,
        )

    def log_error(self, request, exc: Exception, duration: float, **extra):
        log_event(
            self.logger,
            "http_error",
            level="error",
            method=request.method,
            path=request.url.path,
            error=str(exc),
            duration_ms=round(duration * 1000, 3),
            **extra,
        )
