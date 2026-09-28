import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .alerts import AlertManager
from .metrics import MetricsCollector, TimeSeriesStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/observability", tags=["observability"])

_metrics = MetricsCollector()
_store = _metrics.store
_alerts = AlertManager()


class MetricResponse(BaseModel):
    metric_name: str
    value: float
    timestamp: float
    labels: dict[str, str] = {}


class DashboardSummary(BaseModel):
    gpu_utilization: float = 0.0
    tensor_norm: float = 0.0
    tokens_per_second: float = 0.0
    api_requests_per_second: float = 0.0
    benchmark_score: float = 0.0
    dataset_size: int = 0
    experiment_count: int = 0
    active_alerts: int = 0


_summary = DashboardSummary()


def _update_summary() -> None:
    _summary.gpu_utilization = _metrics.get_latest("gpu_utilization") or 0.0
    _summary.tensor_norm = _metrics.get_latest("tensor_norm") or 0.0
    _summary.tokens_per_second = _metrics.get_latest("tokens_per_second") or 0.0
    _summary.api_requests_per_second = _metrics.get_latest("api_requests") or 0.0
    _summary.benchmark_score = _metrics.get_latest("benchmark_score") or 0.0
    _summary.dataset_size = int(_metrics.get_latest("dataset_size") or 0)
    _summary.experiment_count = int(_metrics.get_latest("experiment_count") or 0)
    _summary.active_alerts = len(_alerts.get_active())


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard() -> DashboardSummary:
    _update_summary()
    return _summary


@router.get("/metrics")
async def list_metrics() -> dict[str, list[MetricResponse]]:
    result: dict[str, list[MetricResponse]] = defaultdict(list)
    for key, points in _store._series.items():
        if not points:
            continue
        latest = points[-1]
        result[key].append(
            MetricResponse(
                metric_name=key,
                value=latest.value,
                timestamp=latest.timestamp,
                labels=latest.labels,
            )
        )
    return dict(result)


@router.get("/metrics/{metric_name}")
async def get_metric(metric_name: str, since: float | None = None, until: float | None = None) -> dict[str, Any]:
    points = _store.query(metric_name, since=since, until=until)
    if not points:
        raise HTTPException(status_code=404, detail="Metric not found")
    return {
        "metric_name": metric_name,
        "points": [
            {"timestamp": p.timestamp, "value": p.value, "labels": p.labels} for p in points
        ],
    }


@router.post("/metrics/gpu")
async def record_gpu(utilization: float, temperature: float = 0.0, memory_used_mb: float = 0.0) -> dict[str, str]:
    _metrics.record("gpu_utilization", utilization)
    _metrics.record("gpu_temperature", temperature)
    _metrics.record("gpu_memory_used_mb", memory_used_mb)
    return {"status": "recorded"}


@router.post("/metrics/tensor")
async def record_tensor(norm: float, layer: int = 0) -> dict[str, str]:
    _metrics.record("tensor_norm", norm, {"layer": str(layer)})
    return {"status": "recorded"}


@router.post("/metrics/tokens")
async def record_tokens(tokens_per_second: float, prompt_tokens: int = 0, completion_tokens: int = 0) -> dict[str, str]:
    _metrics.record("tokens_per_second", tokens_per_second)
    _metrics.record("prompt_tokens", float(prompt_tokens))
    _metrics.record("completion_tokens", float(completion_tokens))
    return {"status": "recorded"}


@router.post("/metrics/api")
async def record_api_request(latency_ms: float, status_code: int, endpoint: str = "") -> dict[str, str]:
    _metrics.increment("api_requests", labels={"status": str(status_code), "endpoint": endpoint})
    _metrics.record("api_latency_ms", latency_ms, {"endpoint": endpoint})
    return {"status": "recorded"}


@router.post("/metrics/benchmark")
async def record_benchmark(score: float, benchmark_name: str = "default") -> dict[str, str]:
    _metrics.record("benchmark_score", score, {"benchmark": benchmark_name})
    return {"status": "recorded"}


@router.post("/metrics/dataset")
async def record_dataset(size: int, domain: str = "default") -> dict[str, str]:
    _metrics.set_gauge("dataset_size", float(size), {"domain": domain})
    return {"status": "recorded"}


@router.post("/metrics/experiment")
async def record_experiment(count: int = 1) -> dict[str, str]:
    _metrics.increment("experiment_count", float(count))
    return {"status": "recorded"}


@router.get("/alerts")
async def list_alerts() -> dict[str, Any]:
    active = _alerts.get_active()
    history = _alerts.get_history(limit=50)
    return {
        "active": [
            {
                "rule_name": a.rule_name,
                "message": a.message,
                "severity": a.severity,
                "timestamp": a.timestamp,
                "acknowledged": a.acknowledged,
                "labels": a.labels,
            }
            for a in active
        ],
        "history": [
            {
                "rule_name": a.rule_name,
                "message": a.message,
                "severity": a.severity,
                "timestamp": a.timestamp,
                "acknowledged": a.acknowledged,
            }
            for a in history
        ],
    }


@router.post("/alerts/{rule_name}/acknowledge")
async def acknowledge_alert(rule_name: str) -> dict[str, str]:
    _alerts.acknowledge(rule_name)
    return {"status": "acknowledged"}


@router.post("/alerts/{rule_name}/resolve")
async def resolve_alert(rule_name: str) -> dict[str, str]:
    _alerts.resolve(rule_name)
    return {"status": "resolved"}


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    checks = {
        "metrics_store": "ready",
        "alert_manager": "ready",
    }
    return {"status": "ready", "checks": checks}
