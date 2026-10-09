import threading
from collections import defaultdict
from typing import Any, Dict, List, Optional


class FailureRateTracker:
    CATEGORY_TIMEOUT = "timeout"
    CATEGORY_TOOL_FAILURE = "tool_failure"
    CATEGORY_MODERATION_BLOCK = "moderation_block"

    def __init__(self):
        self._failures: List[Dict[str, Any]] = []
        self._successes: int = 0
        self._lock = threading.Lock()

    def record_success(self):
        with self._lock:
            self._successes += 1

    def record_failure(self, category: str, details: Optional[str] = None):
        entry = {"category": category, "details": details}
        with self._lock:
            self._failures.append(entry)

    def failure_count(self) -> int:
        return len(self._failures)

    def success_count(self) -> int:
        return self._successes

    def total_requests(self) -> int:
        return self._successes + len(self._failures)

    def overall_failure_rate(self) -> Optional[float]:
        total = self.total_requests()
        if total == 0:
            return None
        return self.failure_count() / total

    def failure_rate_by_category(self) -> Dict[str, Optional[float]]:
        total = self.total_requests()
        if total == 0:
            return {c: None for c in [self.CATEGORY_TIMEOUT, self.CATEGORY_TOOL_FAILURE, self.CATEGORY_MODERATION_BLOCK]}
        counts = defaultdict(int)
        for f in self._failures:
            counts[f["category"]] += 1
        return {cat: counts.get(cat, 0) / total for cat in [self.CATEGORY_TIMEOUT, self.CATEGORY_TOOL_FAILURE, self.CATEGORY_MODERATION_BLOCK]}

    def count_by_category(self) -> Dict[str, int]:
        counts = defaultdict(int)
        for f in self._failures:
            counts[f["category"]] += 1
        return dict(counts)

    def failure_rate_per_category_of_failures(self) -> Dict[str, Optional[float]]:
        total = self.failure_count()
        if total == 0:
            return {c: None for c in [self.CATEGORY_TIMEOUT, self.CATEGORY_TOOL_FAILURE, self.CATEGORY_MODERATION_BLOCK]}
        counts = defaultdict(int)
        for f in self._failures:
            counts[f["category"]] += 1
        return {cat: counts.get(cat, 0) / total for cat in [self.CATEGORY_TIMEOUT, self.CATEGORY_TOOL_FAILURE, self.CATEGORY_MODERATION_BLOCK]}
