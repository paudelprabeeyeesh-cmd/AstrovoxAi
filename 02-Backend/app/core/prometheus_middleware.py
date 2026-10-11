import time
from prometheus_client import Counter, Histogram
from prometheus_client.registry import REGISTRY, DuplicateTimeseries
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request


def _metric(ctor, name, *args, **kwargs):
    """Return an existing collector for `name`, or create it.

    ``app.metrics`` defines several of the same metrics at import time, and
    importing both modules would otherwise raise ``DuplicateTimeseries``.
    """
    try:
        return ctor(name, *args, **kwargs)
    except DuplicateTimeseries:
        for collector, names in list(REGISTRY._collector_to_names.items()):
            if name in names:
                return collector
        raise


REQUEST_COUNT = _metric(Counter, "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = _metric(Histogram, "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])
REQUEST_DURATION_BY_ENDPOINT = _metric(
    Histogram,
    "http_request_duration_by_endpoint_seconds",
    "HTTP request duration by endpoint in seconds",
    ["endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ERROR_COUNT = _metric(Counter, "http_errors_total", "Total HTTP errors", ["method", "endpoint", "status"])
MODEL_USAGE = Counter(
    "model_usage_total",
    "Model usage count",
    ["model", "provider"],
)

LLM_REQUEST_DURATION = _metric(Histogram, 
    "llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["provider", "model", "status", "request_id", "user_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)
TTFT = _metric(Histogram, 
    "ttft_seconds",
    "Time to first token in seconds",
    ["provider", "model", "request_id", "user_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)
TOKENS_PER_SECOND = _metric(Histogram, 
    "tokens_per_second",
    "Tokens per second",
    ["provider", "model", "request_id", "user_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

LLM_REQUESTS_TOTAL = _metric(Counter, 
    "llm_requests_total",
    "Total LLM requests",
    ["provider", "model", "status", "request_id", "user_id"],
)
CACHE_HITS_TOTAL = _metric(Counter, 
    "cache_hits_total",
    "Total cache hits",
    ["request_id", "user_id"],
)
CACHE_MISSES_TOTAL = _metric(Counter, 
    "cache_misses_total",
    "Total cache misses",
    ["request_id", "user_id"],
)
ERROR_TOTAL = _metric(Counter, 
    "error_total",
    "Total errors",
    ["endpoint", "status_code", "request_id", "user_id"],
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        endpoint = request.url.path
        request_id = getattr(request.state, "request_id", "") or request.headers.get("X-Request-ID", "")
        user_id = request.headers.get("X-User-ID", "")

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)
        REQUEST_DURATION_BY_ENDPOINT.labels(endpoint=endpoint).observe(duration)

        if response.status_code >= 400:
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
            ).inc()
            ERROR_TOTAL.labels(
                endpoint=endpoint,
                status_code=response.status_code,
                request_id=request_id,
                user_id=user_id,
            ).inc()

        return response