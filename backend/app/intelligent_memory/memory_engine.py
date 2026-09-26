"""Memory engine for intelligent context retention."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryRecord:
    record_id: str
    user_id: str
    content: str
    embedding: Optional[List[float]] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryEngine:
    def __init__(self) -> None:
        self._records: Dict[str, MemoryRecord] = {}
        self._user_index: Dict[str, List[str]] = {}

    def add_record(self, record: MemoryRecord) -> None:
        self._records[record.record_id] = record
        self._user_index.setdefault(record.user_id, []).append(record.record_id)

    def get_records(self, user_id: str, limit: int = 50) -> List[MemoryRecord]:
        record_ids = self._user_index.get(user_id, [])[-limit:]
        return [self._records[rid] for rid in record_ids if rid in self._records]

    def search(self, user_id: str, query: str, limit: int = 10) -> List[MemoryRecord]:
        records = self.get_records(user_id, limit=100)
        scored = [(record, record.content.lower().count(query.lower())) for record in records]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [record for record, _ in scored[:limit]]


memory_engine = MemoryEngine()
