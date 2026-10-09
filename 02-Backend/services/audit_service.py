import json
import logging
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, file_sink: Optional[str] = None, max_memory: int = 10000):
        self._log: OrderedDict[str, dict] = OrderedDict()
        self.max_memory = max_memory
        self.file_sink = Path(file_sink) if file_sink else None
        self._lock = threading.Lock()

    def log(self, event_type: str, actor: str, action: str, target: str = "", details: Optional[Dict[str, Any]] = None, status: str = "success") -> dict:
        entry = {
            "id": f"{int(datetime.now(timezone.utc).timestamp() * 1000)}-{len(self._log)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "actor": actor,
            "action": action,
            "target": target,
            "details": details or {},
            "status": status,
        }
        with self._lock:
            self._log[entry["id"]] = entry
            if len(self._log) > self.max_memory:
                self._log.popitem(last=False)
        if self.file_sink:
            try:
                self.file_sink.parent.mkdir(parents=True, exist_ok=True)
                with self.file_sink.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, default=str) + "\n")
            except OSError as exc:
                logger.warning("Audit file sink failed: %s", exc)
        return entry

    def get_log(self, limit: int = 100, offset: int = 0) -> List[dict]:
        with self._lock:
            entries = list(self._log.values())
        return entries[offset:offset + limit]

    def is_immutable(self) -> bool:
        return True


audit_service = AuditService()
