"""Grafana dashboard JSON definitions."""
import json
from typing import Dict


def _panel(title: str, expr: str, type_: str = "graph", yaxes_format: str = "short") -> Dict:
    return {
        "title": title,
        "type": type_,
        "datasource": "Prometheus",
        "targets": [{"expr": expr, "refId": "A"}],
        "yaxes": [{"format": yaxes_format}, {"format": "short"}],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
    }


DASHBOARDS: Dict[str, Dict] = {
    "astrovox-overview": {
        "title": "AstrovoxAI Overview",
        "uid": "astrovox-overview",
        "timezone": "browser",
        "schemaVersion": 38,
        "panels": [
            {**_panel("Request Rate", 'sum(rate(http_requests_total[5m])) by (status)')},
            {**_panel("P95 Latency", 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, path))', yaxes_format="s")},
            {**_panel("Error Budget Remaining", 'error_budget_remaining')},
            {**_panel("Active Users", 'active_users')},
        ],
    },
    "astrovox-reliability": {
        "title": "AstrovoxAI Reliability",
        "uid": "astrovox-reliability",
        "timezone": "browser",
        "schemaVersion": 38,
        "panels": [
            {**_panel("Disaster Recovery Last Run", 'disaster_recovery_last_run_success')},
            {**_panel("Backup Last Success Timestamp", 'backup_last_success_timestamp')},
            {**_panel("Backup Duration", 'rate(backup_duration_seconds_sum[5m])')},
            {**_panel("Incident Count", 'sum(incident_manager_total_incidents)')},
        ],
    },
    "astrovox-cost": {
        "title": "AstrovoxAI Cost Optimization",
        "uid": "astrovox-cost",
        "timezone": "browser",
        "schemaVersion": 38,
        "panels": [
            {**_panel("Cost Per Request", 'cost_per_request_usd')},
            {**_panel("Queue Depth", 'queue_depth')},
            {**_panel("Model Latency", 'model_latency_seconds_sum')},
        ],
    },
    "astrovox-capacity": {
        "title": "AstrovoxAI Capacity Planning",
        "uid": "astrovox-capacity",
        "timezone": "browser",
        "schemaVersion": 38,
        "panels": [
            {**_panel("Capacity Utilization", 'capacity_utilization_ratio')},
            {**_panel("Memory Usage", 'process_resident_memory_bytes{job="astrovox-backend"}')},
            {**_panel("CPU Usage", 'rate(process_cpu_seconds_total[5m])')},
        ],
    },
}


def write_dashboards(path: str):
    os.makedirs(path, exist_ok=True)
    for uid, dashboard in DASHBOARDS.items():
        with open(os.path.join(path, f"{uid}.json"), "w", encoding="utf-8") as f:
            json.dump(dashboard, f, indent=2)
