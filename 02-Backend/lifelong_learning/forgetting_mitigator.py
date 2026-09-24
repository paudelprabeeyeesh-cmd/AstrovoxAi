from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import math
import time


@dataclass
class ImportanceRecord:
    item_id: str
    importance: float
    last_reviewed: float = field(default_factory=time.time)
    review_count: int = 0


class ForgettingMitigator:
    def __init__(self, base_interval: float = 60.0, decay: float = 0.9) -> None:
        self.base_interval = base_interval
        self.decay = decay
        self._records: Dict[str, ImportanceRecord] = {}
        self._reviews: List[Dict[str, Any]] = []

    def record_importance(self, item_id: str, importance: float) -> ImportanceRecord:
        if item_id in self._records:
            record = self._records[item_id]
            record.importance = max(record.importance, importance)
            return record
        record = ImportanceRecord(item_id=item_id, importance=importance)
        self._records[item_id] = record
        return record

    def get_review_schedule(self, item_id: str) -> Optional[Dict[str, Any]]:
        if item_id not in self._records:
            return None
        record = self._records[item_id]
        next_interval = self.base_interval * (self.decay ** record.review_count)
        next_review = record.last_reviewed + next_interval
        return {
            "item_id": item_id,
            "next_review": next_review,
            "interval": next_interval,
            "importance": record.importance,
            "review_count": record.review_count,
        }

    def review(self, item_id: str) -> Optional[Dict[str, Any]]:
        if item_id not in self._records:
            return None
        record = self._records[item_id]
        record.last_reviewed = time.time()
        record.review_count += 1
        entry = {
            "item_id": item_id,
            "reviewed_at": record.last_reviewed,
            "review_count": record.review_count,
        }
        self._reviews.append(entry)
        return entry

    def compute_forgetting_curve(
        self, item_id: str, elapsed: float
    ) -> Optional[float]:
        if item_id not in self._records:
            return None
        record = self._records[item_id]
        strength = record.importance * (self.decay ** (elapsed / self.base_interval))
        return max(0.0, strength)

    def get_due_items(self, now: Optional[float] = None) -> List[str]:
        now = now if now is not None else time.time()
        due = []
        for item_id, record in self._records.items():
            interval = self.base_interval * (self.decay ** record.review_count)
            if now - record.last_reviewed >= interval:
                due.append(item_id)
        return due

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._records)
        avg_importance = (
            sum(r.importance for r in self._records.values()) / total if total else 0.0
        )
        return {
            "total_items": total,
            "average_importance": round(avg_importance, 4),
            "total_reviews": len(self._reviews),
        }
