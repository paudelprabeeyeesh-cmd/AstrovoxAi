"""Change Data Capture for real-time data synchronization."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class DataChange:
    change_id: str
    table: str
    change_type: ChangeType
    primary_key: Dict[str, Any]
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    checksum: str = ""

    def __post_init__(self) -> None:
        if not self.checksum:
            data = str(self.table) + str(self.change_type.value) + str(self.primary_key) + str(self.new_values)
            self.checksum = hashlib.sha256(data.encode()).hexdigest()


class ChangeDataCapture:
    def __init__(self) -> None:
        self._changes: List[DataChange] = []
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._positions: Dict[str, int] = {}

    def emit(self, change: DataChange) -> None:
        self._changes.append(change)
        self._notify(change)

    def subscribe(self, table: str, handler: Callable[..., Any]) -> None:
        self._handlers[table] = handler

    def get_changes(self, table: str, since_position: int = 0) -> List[DataChange]:
        return [c for c in self._changes if c.table == table and self._changes.index(c) > since_position]

    def get_position(self, table: str) -> int:
        return self._positions.get(table, 0)

    def set_position(self, table: str, position: int) -> None:
        self._positions[table] = position

    def _notify(self, change: DataChange) -> None:
        handler = self._handlers.get(change.table)
        if handler:
            try:
                handler(change)
            except Exception:
                logger.exception("CDC handler failed for table %s", change.table)


cdc = ChangeDataCapture()
