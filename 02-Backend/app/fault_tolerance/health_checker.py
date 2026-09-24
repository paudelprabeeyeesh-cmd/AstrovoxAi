import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class HealthStatus:
    def __init__(self, name: str, healthy: bool, message: str = "", details: Dict[str, Any] | None = None):
        self.name = name
        self.healthy = healthy
        self.message = message
        self.details = details if isinstance(details, dict) else {}

    def __repr__(self) -> str:
        return f"HealthStatus(name={self.name!r}, healthy={self.healthy})"


class HealthChecker:
    def __init__(self):
        self.checks: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, check: Callable[..., Any]) -> None:
        self.checks[name] = check

    def check(self, name: str, *args: Any, **kwargs: Any) -> HealthStatus:
        if name not in self.checks:
            raise ValueError(f"Health check '{name}' is not registered")
        try:
            details = self.checks[name](*args, **kwargs)
            return HealthStatus(name=name, healthy=True, details=details)
        except Exception as exc:
            return HealthStatus(name=name, healthy=False, message=str(exc))

    def run_all(self) -> Dict[str, HealthStatus]:
        results = {}
        for name in self.checks:
            results[name] = self.check(name)
        return results

    def is_healthy(self) -> bool:
        return all(status.healthy for status in self.run_all().values())
