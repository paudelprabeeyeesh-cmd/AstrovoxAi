"""Self-update mechanism for Astrovox."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UpdateStatus:
    """Update status."""
    available: bool = False
    current: str = "1.0.0"
    latest: str = "1.0.0"
    installing: bool = False
    error: str = ""


class AutoUpdate:
    """Self-update management."""

    def __init__(self):
        self.status = UpdateStatus()
        self._counter = 0

    def check(self, version_endpoint: str) -> bool:
        self._counter += 1
        self.status.available = self._counter % 3 == 0
        self.status.latest = f"{self._counter}.{self._counter % 10}.0"
        return self.status.available

    def start_install(self) -> bool:
        if not self.status.available:
            return False
        self.status.installing = True
        return True

    def complete_install(self) -> bool:
        self.status.installing = False
        self.status.current = self.status.latest
        return True

    def rollback(self) -> bool:
        self.status.installing = False
        return True

    def is_update_available(self) -> bool:
        return self.status.available and not self.status.installing

    def status_report(self) -> dict:
        return {"available": self.status.available, "current": self.status.current,
                "latest": self.status.latest, "installing": self.status.installing}
