"""Prometheus metrics for AstrovoxAI backend."""

import time
from functools import wraps

try:
    from prometheus_client.registry import DuplicateTimeseries, REGISTRY
except ImportError:
    DuplicateTimeseries = Exception
    REGISTRY = None

PROMETHEUS_AVAILABLE = False
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    pass


def _get_existing(name):
    if REGISTRY is None:
        return None
    try:
        return REGISTRY.get(name)
    except Exception:
        return None


def _create_or_get(metric_factory, name, *args, **kwargs):
    existing = _get_existing(name)
    if existing is not None:
        return existing
    try:
        return metric_factory(name, *args, **kwargs)
    except DuplicateTimeseries:
        existing = _get_existing(name)
        return existing
    except Exception:
        return None


if PROMETHEUS_AVAILABLE:
    http_requests_total = _create_or_get(
        Counter,
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )

    http_request_duration = _create_or_get(
        Histogram,
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    http_errors_total = _create_or_get(
        Counter,
        "http_errors_total",
        "Total HTTP error responses (5xx)",
        ["method", "endpoint", "status"],
    )

    active_connections = _create_or_get(
        Gauge,
        "active_connections",
        "Number of currently active HTTP connections",
    )

    websocket_connections_total = _create_or_get(
        Counter,
        "websocket_connections_total",
        "Total WebSocket connection events",
        ["event"],
    )

    active_users = _create_or_get(
        Gauge,
        "active_users",
        "Number of active users in the last 5 minutes",
    )

    ai_requests_total = _create_or_get(
        Counter,
        "ai_requests_total",
        "Total AI API requests",
        ["model", "status"],
    )

    ai_tokens_total = _create_or_get(
        Counter,
        "ai_tokens_total",
        "Total AI tokens consumed",
        ["model"],
    )

    ai_request_duration_seconds = _create_or_get(
        Histogram,
        "ai_request_duration_seconds",
        "AI API request duration in seconds",
        ["model"],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    )

    cache_hits_total = _create_or_get(
        Counter,
        "cache_hits_total",
        "Total cache hits",
        ["backend_type"],
    )

    cache_misses_total = _create_or_get(
        Counter,
        "cache_misses_total",
        "Total cache misses",
        ["backend_type"],
    )

    db_query_duration = _create_or_get(
        Histogram,
        "db_query_duration_seconds",
        "Database query duration in seconds",
        ["operation"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    )

    auth_attempts_total = _create_or_get(
        Counter,
        "auth_attempts_total",
        "Total authentication attempts",
        ["provider", "status"],
    )


def track_request(method: str, endpoint: str, status: int, duration: float):
    if not PROMETHEUS_AVAILABLE:
        return
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    if status >= 500:
        http_errors_total.labels(
            method=method, endpoint=endpoint, status=status
        ).inc()


def track_ai_request(model: str, status: str, tokens: int = 0):
    if not PROMETHEUS_AVAILABLE:
        return
    ai_requests_total.labels(model=model, status=status).inc()
    if tokens > 0:
        ai_tokens_total.labels(model=model).inc(tokens)


def track_ai_duration(model: str, duration: float):
    if not PROMETHEUS_AVAILABLE:
        return
    ai_request_duration_seconds.labels(model=model).observe(duration)


def track_cache_hit(backend_type: str):
    if not PROMETHEUS_AVAILABLE:
        return
    cache_hits_total.labels(backend_type=backend_type).inc()


def track_cache_miss(backend_type: str):
    if not PROMETHEUS_AVAILABLE:
        return
    cache_misses_total.labels(backend_type=backend_type).inc()


def track_db_query(operation: str, duration: float):
    if not PROMETHEUS_AVAILABLE:
        return
    db_query_duration.labels(operation=operation).observe(duration)


def track_auth_attempt(provider: str, status: str):
    if not PROMETHEUS_AVAILABLE:
        return
    auth_attempts_total.labels(provider=provider, status=status).inc()


def inc_connections():
    if not PROMETHEUS_AVAILABLE:
        return
    active_connections.inc()


def dec_connections():
    if not PROMETHEUS_AVAILABLE:
        return
    active_connections.dec()


def track_websocket_event(event: str):
    if not PROMETHEUS_AVAILABLE:
        return
    websocket_connections_total.labels(event=event).inc()


def track_error(method: str, endpoint: str, status: int):
    if not PROMETHEUS_AVAILABLE:
        return
    http_errors_total.labels(method=method, endpoint=endpoint, status=status).inc()


def get_metrics():
    if PROMETHEUS_AVAILABLE:
        return generate_latest()
    return b"# Prometheus client not available\n"


try:
    from prometheus_client import CONTENT_TYPE_LATEST
except ImportError:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"


def track_request_decorator(endpoint: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            method = request.method if request else "UNKNOWN"
            start = time.time()
            try:
                response = await func(*args, **kwargs)
                duration = time.time() - start
                status = response.status_code if hasattr(response, "status_code") else 200
                track_request(method, endpoint, status, duration)
                return response
            except Exception as _e:  # noqa: BLE001
                duration = time.time() - start
                track_request(method, endpoint, 500, duration)
                raise
        return wrapper
    return decorator
