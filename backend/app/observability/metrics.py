from prometheus_client import Counter, Gauge, Histogram, start_http_server

REQUEST_COUNT = Counter("app_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("app_request_latency_seconds", "Request latency", ["endpoint"])
ACTIVE_USERS = Gauge("app_active_users", "Active users")


def record_request(method: str, endpoint: str, status: str, latency: float) -> None:
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)


def start_metrics_server(port: int = 8000) -> None:
    start_http_server(port)
