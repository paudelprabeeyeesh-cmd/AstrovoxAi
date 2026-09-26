"""Analysis result repository for caching and history."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()


class AnalysisRepository:
    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []

    def store(self, analysis_type: str, target: str, result: dict[str, Any]) -> dict[str, Any]:
        entry = {
            "id": f"{analysis_type}_{target}_{len(self.results)}",
            "type": analysis_type,
            "target": target,
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with _LOCK:
            self.results.append(entry)
        return entry

    def get_latest(self, analysis_type: str, target: str) -> dict[str, Any] | None:
        with _LOCK:
            for entry in reversed(self.results):
                if entry["type"] == analysis_type and entry["target"] == target:
                    return entry
        return None

    def history(self, analysis_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with _LOCK:
            data = self.results
        if analysis_type:
            data = [r for r in data if r["type"] == analysis_type]
        return data[-limit:]
