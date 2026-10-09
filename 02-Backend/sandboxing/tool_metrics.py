import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ToolMetrics:
    tool_name: str
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0.0
    last_call_at: Optional[float] = None
    last_status: Optional[str] = None
    pending_approvals: int = 0
    circuit_breaker_rejections: int = 0

    @property
    def avg_duration_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_duration_ms / self.total_calls

    @property
    def error_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.failure_count / self.total_calls

    @property
    def health_status(self) -> str:
        if self.total_calls == 0:
            return "unknown"
        if self.error_rate > 0.5:
            return "unhealthy"
        if self.error_rate > 0.2:
            return "degraded"
        return "healthy"


class ToolMetricsCollector:
    def __init__(self) -> None:
        self._metrics: Dict[str, ToolMetrics] = {}
        self._lock = threading.Lock()

    def record_call(self, tool_name: str, duration_ms: float, status: str) -> None:
        with self._lock:
            if tool_name not in self._metrics:
                self._metrics[tool_name] = ToolMetrics(tool_name=tool_name)
            m = self._metrics[tool_name]
            m.total_calls += 1
            m.total_duration_ms += duration_ms
            m.last_call_at = time.time()
            m.last_status = status
            if status in ("approved", "success"):
                m.success_count += 1
            elif status in ("error", "blocked", "denied"):
                m.failure_count += 1

    def record_approval_pending(self, tool_name: str) -> None:
        with self._lock:
            if tool_name not in self._metrics:
                self._metrics[tool_name] = ToolMetrics(tool_name=tool_name)
            self._metrics[tool_name].pending_approvals += 1

    def record_approval_completed(self, tool_name: str) -> None:
        with self._lock:
            if tool_name not in self._metrics:
                self._metrics[tool_name] = ToolMetrics(tool_name=tool_name)
            m = self._metrics[tool_name]
            m.pending_approvals = max(0, m.pending_approvals - 1)

    def record_circuit_breaker_rejection(self, tool_name: str) -> None:
        with self._lock:
            if tool_name not in self._metrics:
                self._metrics[tool_name] = ToolMetrics(tool_name=tool_name)
            self._metrics[tool_name].circuit_breaker_rejections += 1

    def get(self, tool_name: str) -> Optional[ToolMetrics]:
        with self._lock:
            return self._metrics.get(tool_name)

    def get_all(self) -> Dict[str, ToolMetrics]:
        with self._lock:
            return dict(self._metrics)

    def reset(self, tool_name: str) -> None:
        with self._lock:
            if tool_name in self._metrics:
                self._metrics[tool_name] = ToolMetrics(tool_name=tool_name)


tool_metrics = ToolMetricsCollector()
