"""Queue depth monitor."""

import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("astrovox.queue_depth")


class QueueDepthMonitor:
    """Monitor queue depths and alert on threshold breaches."""

    def __init__(self, max_history: int = 1000, alert_threshold: int = 1000) -> None:
        self._queues: Dict[str, Deque[int]] = {}
        self._max_history = max_history
        self._alert_threshold = alert_threshold
        self._alerts: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def register_queue(self, name: str) -> None:
        with self._lock:
            if name not in self._queues:
                self._queues[name] = deque(maxlen=self._max_history)

    def record(self, name: str, depth: int) -> None:
        with self._lock:
            if name not in self._queues:
                self.register_queue(name)
            self._queues[name].append(depth)
            if depth > self._alert_threshold:
                self._alerts.append({
                    "queue": name,
                    "depth": depth,
                    "timestamp": time.time(),
                })

    def get_depth(self, name: str) -> Optional[int]:
        with self._lock:
            history = self._queues.get(name)
            return history[-1] if history else None

    def get_history(self, name: str, limit: int = 100) -> List[int]:
        with self._lock:
            history = self._queues.get(name, deque())
            return list(history)[-limit:]

    def get_stats(self, name: str) -> Dict[str, Any]:
        with self._lock:
            history = list(self._queues.get(name, []))
            if not history:
                return {"queue": name, "current": 0, "avg": 0, "max": 0, "min": 0}
            return {
                "queue": name,
                "current": history[-1],
                "avg": round(sum(history) / len(history), 2),
                "max": max(history),
                "min": min(history),
            }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {name: self.get_stats(name) for name in self._queues}

    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return self._alerts[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._queues.clear()
            self._alerts.clear()


queue_depth_monitor = QueueDepthMonitor()
