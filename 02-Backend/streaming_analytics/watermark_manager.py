from typing import Any, Dict, Optional


class WatermarkManager:
    def __init__(self, max_lateness: float = 0.0):
        self._watermark: float = float("-inf")
        self._max_lateness = max_lateness
        self._event_counts: Dict[str, int] = {}
        self._late_counts: Dict[str, int] = {}

    def update_watermark(self, timestamp: float) -> float:
        if timestamp > self._watermark:
            self._watermark = timestamp
        return self._watermark

    def watermark(self) -> float:
        return self._watermark

    def is_late(self, event_timestamp: float) -> bool:
        return event_timestamp < (self._watermark - self._max_lateness)

    def record_event(self, event_type: str) -> None:
        self._event_counts[event_type] = self._event_counts.get(event_type, 0) + 1

    def record_late(self, event_type: str) -> None:
        self._late_counts[event_type] = self._late_counts.get(event_type, 0) + 1

    def late_count(self, event_type: str) -> int:
        return self._late_counts.get(event_type, 0)

    def total_event_count(self, event_type: str) -> int:
        return self._event_counts.get(event_type, 0)

    def late_ratio(self, event_type: str) -> float:
        total = self.total_event_count(event_type)
        if total == 0:
            return 0.0
        return self.late_count(event_type) / total

    def advance(self, timestamp: float) -> Dict[str, Any]:
        old = self._watermark
        self.update_watermark(timestamp)
        return {
            "previous_watermark": old,
            "current_watermark": self._watermark,
            "advanced": self._watermark > old,
        }
