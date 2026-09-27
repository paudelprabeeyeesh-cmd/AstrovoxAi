"""AI memory engine."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIMemoryRecord:
    record_id: str
    user_id: str
    content: str
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AIMemoryEngine:
    def __init__(self) -> None:
        self._records: Dict[str, AIMemoryRecord] = {}
        self._user_index: Dict[str, List[str]] = {}

    def add_record(self, record: AIMemoryRecord) -> None:
        self._records[record.record_id] = record
        self._user_index.setdefault(record.user_id, []).append(record.record_id)

    def get_records(self, user_id: str, limit: int = 50) -> List[AIMemoryRecord]:
        record_ids = self._user_index.get(user_id, [])[-limit:]
        return [self._records[rid] for rid in record_ids if rid in self._records]


ai_memory_engine = AIMemoryEngine()
