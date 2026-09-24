"""Monitoring dashboard configuration and helpers for AstrovoxAI backend.

Provides:
- DASHBOARD_PANELS: panel definitions consumable by Grafana or custom UIs.
- get_dashboard(): returns the full dashboard payload including metrics queries
  and health summary.
- metrics_summary(): lightweight current-state snapshot from Prometheus counters.
"""

import time
from typing import Any, Dict, List

from app.health import health_service
from app.metrics import PROMETHEUS_AVAILABLE, get_metrics

DASHBOARD_PANELS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
            {
                "expr": "sum(rate(http_requests_total[1m])) by (endpoint)",
                "legendFormat": "{{endpoint}}",
            }
        ],
        "unit": "rps",
    },
    {
        "id": 2,
        "title": "P95 Latency",
        "type": "graph",
        "targets": [
            {
                "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))",
                "legendFormat": "{{endpoint}}",
            }
        ],
        "unit": "s",
        "alert": {
            "name": "SlowResponses",
            "condition": "avg > 2s over 10m",
            "severity": "warning",
        },
    },
    {
        "id": 3,
        "title": "Error Rate (5xx)",
        "type": "graph",
        "targets": [
            {
                "expr": "sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m]))",
                "legendFormat": "5xx error rate",
            }
        ],
        "unit": "percentunit",
    },
    {
        "id": 4,
        "title": "Active Users",
        "type": "graph",
        "targets": [
            {"expr": "active_users", "legendFormat": "active users"}
        ],
    },
    {
        "id": 5,
        "title": "AI Requests by Model",
        "type": "graph",
        "targets": [
            {
                "expr": "sum(rate(ai_requests_total[5m])) by (model, status)",
                "legendFormat": "{{model}} - {{status}}",
            }
        ],
    },
    {
        "id": 6,
        "title": "Cache Hit Ratio",
        "type": "graph",
        "targets": [
            {
                "expr": "sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))",
                "legendFormat": "cache hit ratio",
            }
        ],
        "unit": "percentunit",
    },
    {
        "id": 7,
        "title": "Database Query P95",
        "type": "graph",
        "targets": [
            {
                "expr": "histogram_quantile(0.95, sum(rate(db_query_duration_seconds_bucket[5m])) by (le, operation))",
                "legendFormat": "{{operation}}",
            }
        ],
        "unit": "s",
    },
    {
        "id": 8,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
            {
                "expr": "process_resident_memory_bytes{job=\"astravox-backend\"}",
                "legendFormat": "resident memory",
            }
        ],
        "unit": "bytes",
    },
    {
        "id": 9,
        "title": "AI Request P95 Latency",
        "type": "graph",
        "targets": [
            {
                "expr": "histogram_quantile(0.95, sum(rate(ai_request_duration_seconds_bucket[5m])) by (le, model))",
                "legendFormat": "{{model}}",
            }
        ],
        "unit": "s",
    },
    {
        "id": 10,
        "title": "WebSocket Connections",
        "type": "graph",
        "targets": [
            {
                "expr": "sum(rate(websocket_connections_total[1m])) by (event)",
                "legendFormat": "{{event}}",
            }
        ],
        "unit": "rps",
    },
]


def get_dashboard(app=None) -> Dict[str, Any]:
    """Return the full dashboard payload."""
    health_service.app = app
    health = health_service.get_overall_health()
    raw_metrics = get_metrics() if PROMETHEUS_AVAILABLE else b""
    return {
        "dashboard": {
            "title": "AstrovoxAI Backend",
            "uid": "astrovox-backend",
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 2,
            "refresh": "10s",
            "panels": DASHBOARD_PANELS,
        },
        "health": health,
        "metrics_available": PROMETHEUS_AVAILABLE,
        "metrics_raw": raw_metrics.decode("utf-8", errors="replace") if raw_metrics else "",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def metrics_summary() -> Dict[str, Any]:
    """Lightweight snapshot of key metric values (best-effort)."""
    if not PROMETHEUS_AVAILABLE:
        return {"prometheus_available": False}
    try:
        from prometheus_client import REGISTRY
        samples = {}
        for metric in REGISTRY.collect():
            for sample in metric.samples:
                key = sample.name
                if sample.labels:
                    key += ":" + ",".join(f"{k}={v}" for k, v in sample.labels.items())
                samples[key] = sample.value
        return {"prometheus_available": True, "samples": samples}
    except Exception as _e:  # noqa: BLE001
        return {"prometheus_available": True, "error": str(_e)}
