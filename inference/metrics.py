"""Prometheus metrics for inference server."""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Response

# Model info
model_info = Info("inference_model", "Inference model information")

# Request metrics
request_count = Counter(
    "inference_requests_total",
    "Total inference requests",
    ["endpoint", "method", "status"],
)

request_duration = Histogram(
    "inference_request_duration_seconds",
    "Request duration in seconds",
    ["endpoint", "method"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Model metrics
model_load_time = Gauge(
    "inference_model_load_time_seconds",
    "Time taken to load the model",
)

model_memory_usage = Gauge(
    "inference_model_memory_bytes",
    "Current memory usage of the model in bytes",
)

model_queue_size = Gauge(
    "inference_queue_size",
    "Current size of the inference queue",
)

# Token metrics
token_count = Counter(
    "inference_tokens_total",
    "Total tokens processed",
    ["type"],
)

tokens_per_second = Histogram(
    "inference_tokens_per_second",
    "Tokens generated per second",
    buckets=[10, 25, 50, 100, 200, 500, 1000],
)

# Error metrics
error_count = Counter(
    "inference_errors_total",
    "Total inference errors",
    ["error_type", "endpoint"],
)

# GPU metrics (if available)
gpu_utilization = Gauge(
    "inference_gpu_utilization_percent",
    "GPU utilization percentage",
    ["device"],
)

gpu_memory_used = Gauge(
    "inference_gpu_memory_used_bytes",
    "GPU memory used in bytes",
    ["device"],
)

gpu_memory_total = Gauge(
    "inference_gpu_memory_total_bytes",
    "Total GPU memory in bytes",
    ["device"],
)

# Active requests
active_requests = Gauge(
    "inference_active_requests",
    "Currently active inference requests",
)


def get_metrics_response() -> Response:
    """Return Prometheus metrics response."""
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
