"""Prometheus metrics registration helpers."""
from prometheus_client import Counter, Gauge, Histogram, Summary

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path", "status"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
ERROR_COUNT = Counter(
    "errors_total",
    "Total application errors",
    ["module", "error_type"],
)
ACTIVE_USERS = Gauge(
    "active_users",
    "Currently active users",
)
QUEUE_DEPTH = Gauge(
    "queue_depth",
    "Current async queue depth",
    ["queue_name"],
)
MODEL_LATENCY = Summary(
    "model_latency_seconds",
    "AI model inference latency in seconds",
    ["model", "provider"],
)
BACKUP_STATUS = Gauge(
    "backup_last_success_timestamp",
    "Unix timestamp of last successful backup",
)
BACKUP_DURATION = Histogram(
    "backup_duration_seconds",
    "Backup operation duration in seconds",
    ["backup_type"],
    buckets=(10, 30, 60, 120, 300, 600),
)
DR_RUN_STATUS = Gauge(
    "disaster_recovery_last_run_success",
    "1 if last DR drill succeeded, 0 otherwise",
)
COST_PER_REQUEST = Gauge(
    "cost_per_request_usd",
    "Estimated cost per request in USD",
    ["provider", "model"],
)


def register_default_metrics():
    """Ensure default metrics are registered with the Prometheus registry."""
    from prometheus_client import REGISTRY
    for metric in (
        REQUEST_DURATION,
        REQUEST_COUNT,
        ERROR_COUNT,
        ACTIVE_USERS,
        QUEUE_DEPTH,
        MODEL_LATENCY,
        BACKUP_STATUS,
        BACKUP_DURATION,
        DR_RUN_STATUS,
        COST_PER_REQUEST,
    ):
        try:
            REGISTRY.register(metric)
        except ValueError:
            pass
