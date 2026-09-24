import logging
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self):
        self._entries: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()

    def schedule(self, entry_id: str, run_at: str, payload: Dict[str, Any], recurrence: Optional[str] = None) -> dict:
        entry = {
            "entry_id": entry_id,
            "run_at": run_at,
            "payload": payload,
            "recurrence": recurrence,
            "status": "scheduled",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._entries[entry_id] = entry
        logger.info("Scheduled entry: %s", entry_id)
        return entry

    def cancel(self, entry_id: str) -> dict:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                raise KeyError(f"Unknown entry: {entry_id}")
            entry["status"] = "canceled"
            entry["canceled_at"] = datetime.now(timezone.utc).isoformat()
            logger.info("Canceled entry: %s", entry_id)
            return dict(entry)

    def get_due(self, limit: int = 100) -> List[dict]:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            due = [entry for entry in self._entries.values() if entry["run_at"] <= now and entry["status"] == "scheduled"]
            return [dict(entry) for entry in due[:limit]]

    def reschedule(self, entry_id: str, run_at: str) -> dict:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                raise KeyError(f"Unknown entry: {entry_id}")
            entry["run_at"] = run_at
            entry["status"] = "scheduled"
            entry["rescheduled_at"] = datetime.now(timezone.utc).isoformat()
            logger.info("Rescheduled entry: %s", entry_id)
            return dict(entry)


scheduler_service = SchedulerService()
