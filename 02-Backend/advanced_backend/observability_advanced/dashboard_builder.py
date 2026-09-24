from typing import Any, Dict, List


class DashboardBuilder:
    def __init__(self) -> None:
        self._metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._logs: List[Dict[str, Any]] = []
        self._spans: Dict[str, List[Dict[str, Any]]] = {}

    def add_metrics_snapshot(self, snapshot: Dict[str, Any]) -> None:
        for name, samples in snapshot.get("metrics", {}).items():
            self._metrics.setdefault(name, []).extend(samples)

    def add_logs(self, logs: List[Dict[str, Any]]) -> None:
        self._logs.extend(logs)

    def add_spans(self, spans: Dict[str, List[Dict[str, Any]]]) -> None:
        for trace_id, span_list in spans.items():
            self._spans.setdefault(trace_id, []).extend(span_list)

    def build(self) -> Dict[str, Any]:
        level_counts: Dict[str, int] = {}
        for entry in self._logs:
            level = entry.get("level", "info")
            level_counts[level] = level_counts.get(level, 0) + 1

        return {
            "metrics_summary": {name: len(samples) for name, samples in self._metrics.items()},
            "log_summary": level_counts,
            "span_count": sum(len(v) for v in self._spans.values()),
            "trace_count": len(self._spans),
        }
