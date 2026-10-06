"""Monitoring and health checks for Astrovox."""

from __future__ import annotations

import time


class Monitor:
    """Health and status monitor."""

    def __init__(self):
        self.status = "healthy"
        self.last_check: float = time.time()
        self.checks: list[dict] = []

    def check(self, name: str, fn) -> dict:
        try:
            result = fn()
            ok = True
        except Exception as e:
            result = str(e)
            ok = False
        entry = {"name": name, "ok": ok, "result": result, "timestamp": time.time()}
        self.checks.append(entry)
        self.last_check = entry["timestamp"]
        if not ok:
            self.status = "degraded" if self.status == "healthy" else self.status
        return entry

    def is_healthy(self) -> bool:
        return self.status == "healthy"

    def get_status(self) -> str:
        return self.status

    def recent_checks(self, n: int = 10) -> list[dict]:
        return self.checks[-n:]

    def reset(self) -> None:
        self.checks.clear()
        self.status = "healthy"
        self.last_check = time.time()
