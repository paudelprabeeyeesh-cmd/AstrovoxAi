from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time
import logging
import threading

logger = logging.getLogger(__name__)


@dataclass
class RealtimeMetric:
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class DashboardWidget:
    widget_id: str
    title: str
    metric_name: str
    chart_type: str = "line"
    time_window_seconds: int = 300
    aggregation: str = "avg"


class RealtimeAnalyticsDashboard:
    def __init__(self, max_history: int = 10000, retention_seconds: int = 3600):
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._retention = retention_seconds
        self._lock = threading.RLock()
        self._widgets: Dict[str, DashboardWidget] = {}

    def record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        metric = RealtimeMetric(name=name, value=value, timestamp=time.time(), tags=tags or {})
        with self._lock:
            self._metrics[name].append(metric)
            self._cleanup_expired(name)

    def record_event(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        self.record(name, value, tags)

    def get_metric(self, name: str, time_window_seconds: Optional[int] = None) -> Dict[str, Any]:
        now = time.time()
        window = time_window_seconds or self._retention
        with self._lock:
            metrics = [m for m in self._metrics.get(name, []) if now - m.timestamp <= window]
        if not metrics:
            return {'name': name, 'count': 0, 'avg': 0.0, 'min': 0.0, 'max': 0.0, 'latest': 0.0, 'window_seconds': window}
        values = [m.value for m in metrics]
        return {
            'name': name,
            'count': len(values),
            'avg': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'latest': values[-1],
            'window_seconds': window,
        }

    def get_timeseries(self, name: str, time_window_seconds: Optional[int] = None, bucket_seconds: int = 60) -> List[Dict[str, Any]]:
        now = time.time()
        window = time_window_seconds or self._retention
        with self._lock:
            metrics = [m for m in self._metrics.get(name, []) if now - m.timestamp <= window]
        if not metrics:
            return []
        buckets: Dict[int, List[float]] = defaultdict(list)
        for m in metrics:
            bucket_key = int(m.timestamp // bucket_seconds) * bucket_seconds
            buckets[bucket_key].append(m.value)
        series = []
        for bucket_key in sorted(buckets.keys()):
            values = buckets[bucket_key]
            series.append({
                'timestamp': bucket_key,
                'value': sum(values) / len(values),
                'count': len(values),
            })
        return series

    def register_widget(self, widget: DashboardWidget) -> None:
        self._widgets[widget.widget_id] = widget

    def get_widget_data(self, widget_id: str) -> Dict[str, Any]:
        widget = self._widgets.get(widget_id)
        if not widget:
            return {}
        if widget.chart_type == 'line':
            return self.get_timeseries(widget.metric_name, widget.time_window_seconds)
        return self.get_metric(widget.metric_name, widget.time_window_seconds)

    def get_summary(self) -> Dict[str, Any]:
        summary = {}
        with self._lock:
            for name, metrics in self._metrics.items():
                if metrics:
                    values = [m.value for m in metrics]
                    summary[name] = {
                        'count': len(values),
                        'avg': sum(values) / len(values),
                        'latest': values[-1],
                    }
        return summary

    def _cleanup_expired(self, name: str) -> None:
        now = time.time()
        cutoff = now - self._retention
        while self._metrics[name] and self._metrics[name][0].timestamp < cutoff:
            self._metrics[name].popleft()
