"""Enhanced tool analytics with reporting and dashboards."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sandboxing.tool_metrics import tool_metrics
from app.tool_registry import tool_registry

logger = logging.getLogger(__name__)


@dataclass
class ToolAnalyticsReport:
    generated_at: float = field(default_factory=time.time)
    total_tools: int = 0
    healthy_count: int = 0
    degraded_count: int = 0
    unhealthy_count: int = 0
    total_calls: int = 0
    total_success: int = 0
    total_failure: int = 0
    avg_duration_ms: float = 0.0
    top_tools_by_calls: List[Dict[str, Any]] = field(default_factory=list)
    top_tools_by_errors: List[Dict[str, Any]] = field(default_factory=list)
    circuit_breaker_rejections: int = 0
    pending_approvals: int = 0

    @property
    def overall_error_rate(self) -> float:
        return self.total_failure / self.total_calls if self.total_calls else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_tools": self.total_tools,
            "health": {
                "healthy": self.healthy_count,
                "degraded": self.degraded_count,
                "unhealthy": self.unhealthy_count,
            },
            "calls": {
                "total": self.total_calls,
                "success": self.total_success,
                "failure": self.total_failure,
                "error_rate": round(self.overall_error_rate, 4),
            },
            "performance": {
                "avg_duration_ms": round(self.avg_duration_ms, 2),
            },
            "top_by_calls": self.top_tools_by_calls[:10],
            "top_by_errors": self.top_tools_by_errors[:10],
            "circuit_breaker_rejections": self.circuit_breaker_rejections,
            "pending_approvals": self.pending_approvals,
        }


class ToolAnalytics:
    def generate_report(self, since_seconds: Optional[float] = None) -> ToolAnalyticsReport:
        all_metrics = tool_metrics.get_all()
        report = ToolAnalyticsReport(total_tools=len(tool_registry._tools))
        total_duration = 0.0
        tool_entries = []
        for name, m in all_metrics.items():
            report.total_calls += m.total_calls
            report.total_success += m.success_count
            report.total_failure += m.failure_count
            total_duration += m.total_duration_ms
            if m.health_status == "healthy":
                report.healthy_count += 1
            elif m.health_status == "degraded":
                report.degraded_count += 1
            elif m.health_status == "unhealthy":
                report.unhealthy_count += 1
            report.circuit_breaker_rejections += m.circuit_breaker_rejections
            report.pending_approvals += m.pending_approvals
            tool_entries.append({
                "tool_name": name,
                "total_calls": m.total_calls,
                "error_rate": m.error_rate,
                "avg_duration_ms": m.avg_duration_ms,
                "health": m.health_status,
            })
        if report.total_calls > 0:
            report.avg_duration_ms = total_duration / report.total_calls
        tool_entries.sort(key=lambda x: x["total_calls"], reverse=True)
        report.top_tools_by_calls = tool_entries[:10]
        tool_entries.sort(key=lambda x: x["error_rate"], reverse=True)
        report.top_tools_by_errors = [t for t in tool_entries if t["error_rate"] > 0][:10]
        return report

    def get_tool_leaderboard(self, metric: str = "total_calls", limit: int = 10) -> List[Dict[str, Any]]:
        all_metrics = tool_metrics.get_all()
        entries = []
        for name, m in all_metrics.items():
            entries.append({
                "tool_name": name,
                "total_calls": m.total_calls,
                "success_count": m.success_count,
                "failure_count": m.failure_count,
                "error_rate": m.error_rate,
                "avg_duration_ms": m.avg_duration_ms,
                "health": m.health_status,
            })
        entries.sort(key=lambda x: x.get(metric, 0), reverse=True)
        return entries[:limit]

    def get_health_distribution(self) -> Dict[str, int]:
        all_metrics = tool_metrics.get_all()
        dist = {"healthy": 0, "degraded": 0, "unhealthy": 0, "unknown": 0}
        for m in all_metrics.values():
            dist[m.health_status] = dist.get(m.health_status, 0) + 1
        return dist

    def get_slowest_tools(self, limit: int = 10) -> List[Dict[str, Any]]:
        all_metrics = tool_metrics.get_all()
        entries = [
            {"tool_name": name, "avg_duration_ms": m.avg_duration_ms, "total_calls": m.total_calls}
            for name, m in all_metrics.items()
            if m.total_calls > 0
        ]
        entries.sort(key=lambda x: x["avg_duration_ms"], reverse=True)
        return entries[:limit]


tool_analytics = ToolAnalytics()
