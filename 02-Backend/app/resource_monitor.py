"""Resource monitor endpoint helper."""

import logging
import os
import platform
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("astrovox.resource_monitor")


class ResourceMonitor:
    """Monitor system resources and expose endpoint-ready summaries."""

    def __init__(self) -> None:
        self._snapshots: list[dict] = []
        self._max_snapshots = 500

    def take_snapshot(self) -> dict:
        snapshot = {
            "timestamp": time.time(),
            "cpu_percent": self._get_cpu_percent(),
            "memory_percent": self._get_memory_percent(),
            "memory_used_mb": self._get_memory_used_mb(),
            "open_files": self._get_open_files(),
            "thread_count": threading.active_count(),
            "process_id": os.getpid(),
        }
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
        return snapshot

    def get_current(self) -> dict:
        return self.take_snapshot()

    def get_history(self, limit: int = 100) -> list[dict]:
        return self._snapshots[-limit:]

    def get_summary(self) -> dict:
        if not self._snapshots:
            return {"status": "no_data"}
        latest = self._snapshots[-1]
        return {
            "status": "ok",
            "latest": latest,
            "sample_count": len(self._snapshots),
        }

    def _get_cpu_percent(self) -> float:
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0

    def _get_memory_percent(self) -> float:
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0

    def _get_memory_used_mb(self) -> float:
        try:
            import psutil
            return psutil.virtual_memory().used / (1024 * 1024)
        except ImportError:
            return 0.0

    def _get_open_files(self) -> int:
        try:
            import psutil
            return len(psutil.Process().open_files())
        except ImportError:
            return 0


resource_monitor = ResourceMonitor()
