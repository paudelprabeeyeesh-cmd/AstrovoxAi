<<<<<<< HEAD
"""Resource monitor endpoint helper."""

import logging
import os
import threading
import time

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
=======
"""Resource monitoring for AstrovoxAI backend.

Provides CPU, memory, disk, and network metrics collection.
"""

from __future__ import annotations

import logging
import os
import psutil
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResourceSnapshot:
    cpu_percent: float
    memory_percent: float
    memory_rss_mb: float
    disk_usage_percent: float
    network_sent_mb: float
    network_recv_mb: float
    open_file_descriptors: int
    thread_count: int
    timestamp: float = field(default_factory=time.time)


class ResourceMonitor:
    """Monitors system resources with alerting thresholds."""

    def __init__(self, collection_interval: float = 10.0, alert_callback: Optional[Callable] = None):
        self.collection_interval = collection_interval
        self.alert_callback = alert_callback
        self._snapshots: List[ResourceSnapshot] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._process = psutil.Process(os.getpid())
        self._last_net = psutil.net_io_counters()

    def _collect(self) -> ResourceSnapshot:
        net = psutil.net_io_counters()
        disk = psutil.disk_usage("/")
        mem = self._process.memory_info()
        return ResourceSnapshot(
            cpu_percent=self._process.cpu_percent(),
            memory_percent=self._process.memory_percent(),
            memory_rss_mb=mem.rss / (1024 * 1024),
            disk_usage_percent=disk.percent,
            network_sent_mb=(net.bytes_sent - self._last_net.bytes_sent) / (1024 * 1024),
            network_recv_mb=(net.bytes_recv - self._last_net.bytes_recv) / (1024 * 1024),
            open_file_descriptors=self._process.num_fds() if hasattr(self._process, "num_fds") else 0,
            thread_count=self._process.num_threads(),
        )

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                snapshot = self._collect()
                with self._lock:
                    self._snapshots.append(snapshot)
                    if len(self._snapshots) > 360:
                        self._snapshots = self._snapshots[-360:]
                if snapshot.cpu_percent > 90 or snapshot.memory_percent > 90:
                    if self.alert_callback:
                        self.alert_callback(snapshot)
                self._last_net = psutil.net_io_counters()
            except Exception as exc:  # noqa: BLE001
                logger.error("Resource monitoring error: %s", exc)
            time.sleep(self.collection_interval)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Resource monitor started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def get_snapshot(self) -> ResourceSnapshot:
        return self._collect()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            if not self._snapshots:
                return {}
            recent = self._snapshots[-10:]
            return {
                "cpu_percent_avg": round(sum(s.cpu_percent for s in recent) / len(recent), 2),
                "memory_percent_avg": round(sum(s.memory_percent for s in recent) / len(recent), 2),
                "memory_rss_mb_avg": round(sum(s.memory_rss_mb for s in recent) / len(recent), 2),
                "disk_usage_percent": self._snapshots[-1].disk_usage_percent,
                "open_fds": self._snapshots[-1].open_file_descriptors,
                "threads": self._snapshots[-1].thread_count,
                "sample_count": len(self._snapshots),
            }
>>>>>>> 10617909505295e4a37b817bb54db2364934b978


resource_monitor = ResourceMonitor()
