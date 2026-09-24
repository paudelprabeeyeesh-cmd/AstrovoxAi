import logging
import threading
from collections import defaultdict
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MetricsService:
    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._lock = threading.Lock()

    def increment(self, name: str, value: float = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
            }


metrics_service = MetricsService()
