"""Live cursors for collaborative editing."""

from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CursorPosition:
    user_id: str
    x: float
    y: float
    color: str = "#007bff"
    label: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LiveCursors:
    _cursors: Dict[str, Dict[str, CursorPosition]] = {}

    @classmethod
    def update_cursor(cls, session_id: str, user_id: str, x: float, y: float, color: str = "#007bff", label: str = "") -> CursorPosition:
        cursor = CursorPosition(user_id=user_id, x=x, y=y, color=color, label=label)
        if session_id not in cls._cursors:
            cls._cursors[session_id] = {}
        cls._cursors[session_id][user_id] = cursor
        return cursor

    @classmethod
    def get_session_cursors(cls, session_id: str) -> List[CursorPosition]:
        return list(cls._cursors.get(session_id, {}).values())

    @classmethod
    def remove_cursor(cls, session_id: str, user_id: str) -> None:
        if session_id in cls._cursors:
            cls._cursors[session_id].pop(user_id, None)
