"""Prometheus metrics for AstrovoxAI backend."""

import time
import os
from functools import wraps

# Prometheus availability flag
PROMETHEUS_AVAILABLE = False
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    pass

# Metrics
if PROMETHEUS_AVAILABLE:
    http_requests_total = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"]
    )

    http_request_duration = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )

    active_users = Gauge(
        "active_users",
        "Number of active users in the last 5 minutes"
    )

    ai_requests_total = Counter(
        "ai_requests_total",
        "Total AI API requests",
        ["model", "status"]
    )

    ai_tokens_total = Counter(
        "ai_tokens_total",
        "Total AI tokens consumed",
        ["model"]
    )

    cache_hits_total = Counter(
        "cache_hits_total",
        "Total cache hits",
        ["backend_type"]
    )

    cache_misses_total = Counter(
        "cache_misses_total",
        "Total cache misses",
        ["backend_type"]
    )

    db_query_duration = Histogram(
        "db_query_duration_seconds",
        "Database query duration in seconds",
        ["operation"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
    )

    rate_limit_total = Counter(
        "rate_limit_total",
        "Total rate limit checks",
        ["policy", "identity", "allowed"]
    )

    rate_limit_remaining = Gauge(
        "rate_limit_remaining",
        "Remaining requests in current window",
        ["policy", "identity"]
    )

def get_metrics():
    """Get Prometheus-formatted metrics."""
    if PROMETHEUS_AVAILABLE:
        return generate_latest()
    return b"# Prometheus client not available\n"


def track_ai_request(model: str, status: str, tokens: int = 0):
    """Track AI request metrics."""
    if not PROMETHEUS_AVAILABLE:
        return
    ai_requests_total.labels(model=model, status=status).inc()
    if tokens > 0:
        ai_tokens_total.labels(model=model).inc(tokens)

