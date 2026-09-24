
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from .enhanced import get_organization_analytics, get_user_analytics
from ..metrics import PROMETHEUS_AVAILABLE, get_metrics

logger = logging.getLogger(__name__)


class PerformanceReporter:
    def generate_report(self, org_id: str = None, user_id: str = None, days: int = 7) -> dict:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window_days": days,
            "org_analytics": None,
            "user_analytics": None,
            "metrics": None,
            "summary": {},
        }
        if org_id:
            report["org_analytics"] = get_organization_analytics(org_id, days)
        if user_id:
            report["user_analytics"] = get_user_analytics(user_id, days)
        if PROMETHEUS_AVAILABLE:
            raw = get_metrics()
            report["metrics"] = raw.decode("utf-8", errors="replace") if raw else ""
        report["summary"] = self._summarize(report)
        return report

    def _summarize(self, report: dict) -> dict:
        summary = {"status": "healthy"}
        if report.get("user_analytics"):
            usage = report["user_analytics"].get("usage", {})
            if usage.get("total_requests", 0) > 0:
                summary["total_requests"] = usage.get("total_requests", 0)
                summary["total_tokens"] = usage.get("total_tokens", 0)
                summary["total_cost"] = usage.get("total_cost", 0)
        return summary

    def export_json(self, report: dict) -> str:
        import json
        return json.dumps(report, default=str, indent=2)

    def export_csv(self, report: dict) -> str:
        import csv, io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["metric", "value"])
        summary = report.get("summary", {})
        for k, v in summary.items():
            writer.writerow([k, v])
        return output.getvalue()
