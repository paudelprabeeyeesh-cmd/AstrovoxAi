import contextvars
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

try:
    import structlog as _structlog

    _STRUCTLOG_AVAILABLE = True
except ImportError:
    _STRUCTLOG_AVAILABLE = False


_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)
_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_id", default=None
)
_endpoint: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "endpoint", default=None
)
_latency_ms: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar(
    "latency_ms", default=None
)
_cost: contextvars.ContextVar[Optional[float]] = contextvars.ContextVar(
    "cost", default=None
)


class _StructuredJsonFormatter(logging.Formatter):
    """Format log records as structured JSON using stdlib."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
            "endpoint": getattr(record, "endpoint", None),
            "latency_ms": getattr(record, "latency_ms", None),
            "cost": getattr(record, "cost", None),
        }
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_data["stack_info"] = record.stack_info
        return json.dumps(log_data, default=str)


class _RequestIdFilter(logging.Filter):
    """Inject request-scoped fields from context vars into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get(None)
        record.user_id = _user_id.get(None)
        record.endpoint = _endpoint.get(None)
        record.latency_ms = _latency_ms.get(None)
        record.cost = _cost.get(None)
        return True


_configured = False


def configure_logging() -> logging.Logger:
    """Configure structured JSON logging with rotation and request ID propagation."""
    global _configured
    if _configured:
        return logging.getLogger("astravox")
    _configured = True

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    fmt = os.getenv("LOG_FORMAT", "json").lower()

    if fmt == "structlog" and _STRUCTLOG_AVAILABLE:
        _structlog.configure(
            processors=[
                _structlog.contextvars.merge_contextvars,
                _structlog.processors.add_log_level,
                _structlog.processors.TimeStamper(fmt="iso"),
                _structlog.processors.JSONRenderer(),
            ],
            wrapper_class=_structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=_structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        return _structlog.get_logger("astravox")

    logger = logging.getLogger("astravox")
    logger.setLevel(log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "astravox.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setLevel(log_level)

    formatter = _StructuredJsonFormatter()
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    request_filter = _RequestIdFilter()
    console_handler.addFilter(request_filter)
    file_handler.addFilter(request_filter)

    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        configure_logging()
    return logging.getLogger(name)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get(
            "X-Request-ID", str(uuid.uuid4())
        )
        _request_id.set(request.state.request_id)
        _endpoint.set(f"{request.method} {request.url.path}")

        start = time.perf_counter()
        response = await call_next(request)
        _latency_ms.set(round((time.perf_counter() - start) * 1000, 2))

        response.headers["X-Request-ID"] = request.state.request_id

        logger = logging.getLogger("astravox")
        logger.info(
            "request_completed",
            extra={
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": _latency_ms.get(None),
                "user_id": _user_id.get(None),
            },
        )
        return response


def inject_request_id(request_id: str) -> None:
    _request_id.set(request_id)


def get_request_id() -> Optional[str]:
    return _request_id.get(None)


def inject_user_id(user_id: str) -> None:
    _user_id.set(user_id)


def get_user_id() -> Optional[str]:
    return _user_id.get(None)


def inject_endpoint(endpoint: str) -> None:
    _endpoint.set(endpoint)


def inject_latency_ms(latency_ms: float) -> None:
    _latency_ms.set(round(latency_ms, 2))


def inject_cost(cost: float) -> None:
    _cost.set(round(cost, 6))
