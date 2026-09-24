from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class HealthCheck:
    component: str
    healthy: bool
    detail: str = ""


class SelfHealing:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.checks: List[HealthCheck] = []
        self.retry_counts: Dict[str, int] = {}
        self.handlers: Dict[str, Callable[[str], Any]] = {}

    def register_handler(self, component: str, handler: Callable[[str], Any]) -> None:
        self.handlers[component] = handler

    def check_health(self, component: str, healthy: bool, detail: str = "") -> bool:
        check = HealthCheck(component=component, healthy=healthy, detail=detail)
        self.checks.append(check)
        if not healthy:
            self._attempt_recovery(component)
        return healthy

    def _attempt_recovery(self, component: str) -> bool:
        count = self.retry_counts.get(component, 0)
        if count >= self.max_retries:
            return False
        self.retry_counts[component] = count + 1
        handler = self.handlers.get(component)
        if handler is not None:
            handler(component)
        return True

    def get_health_summary(self) -> Dict[str, Any]:
        total = len(self.checks)
        healthy = sum(1 for c in self.checks if c.healthy)
        return {"total_checks": total, "healthy": healthy, "unhealthy": total - healthy}
