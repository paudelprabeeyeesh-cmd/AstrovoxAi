import contextvars
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from pythonjsonlogger import json as pythonjsonlogger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

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


class _StructuredLogFilter(logging.Filter):
    def filter(self, record):
        record.timestamp = datetime.now(timezone.utc).isoformat()
        record.request_id = _request_id.get(None)
        record.user_id = _user_id.get(None)
        record.endpoint = _endpoint.get(None)
        record.latency_ms = _latency_ms.get(None)
        record.cost = _cost.get(None)
        return True


class StructuredJsonFormatter(pythonjsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if "levelname" in log_record:
            log_record["level"] = log_record.pop("levelname")
        log_record.setdefault("timestamp", getattr(record, "timestamp", None))
        log_record.setdefault("request_id", getattr(record, "request_id", None))
        log_record.setdefault("user_id", getattr(record, "user_id", None))
        log_record.setdefault("endpoint", getattr(record, "endpoint", None))
        log_record.setdefault("latency_ms", getattr(record, "latency_ms", None))
        log_record.setdefault("cost", getattr(record, "cost", None))


_configured = False


def configure_logging():
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredJsonFormatter(
        "%(timestamp)s %(levelname)s %(message)s %(request_id)s %(user_id)s %(endpoint)s %(latency_ms)s %(cost)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(_StructuredLogFilter())

    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        configure_logging()
    return logging.getLogger(name)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        _request_id.set(request.state.request_id)
        _endpoint.set(f"{request.method} {request.url.path}")

        start = time.perf_counter()
        response = await call_next(request)
        _latency_ms.set(round((time.perf_counter() - start) * 1000, 2))

        response.headers["X-Request-ID"] = request.state.request_id
        return response


def inject_request_id(request_id: str):
    _request_id.set(request_id)


def get_request_id() -> Optional[str]:
    return _request_id.get(None)


def inject_user_id(user_id: str):
    _user_id.set(user_id)


def get_user_id() -> Optional[str]:
    return _user_id.get(None)


def inject_endpoint(endpoint: str):
    _endpoint.set(endpoint)


def inject_latency_ms(latency_ms: float):
    _latency_ms.set(round(latency_ms, 2))


def inject_cost(cost: float):
    _cost.set(round(cost, 6))
