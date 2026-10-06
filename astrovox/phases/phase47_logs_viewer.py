"""Centralized log viewer for Astrovox."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    """A log entry."""
    level: str
    message: str
    source: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"level": self.level, "message": self.message, "source": self.source,
                "timestamp": self.timestamp}


class LogViewer:
    """Centralized log storage and viewer."""

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.entries: list[LogEntry] = []

    def log(self, level: str, message: str, source: str = "astrovox") -> None:
        self.entries.append(LogEntry(level=level, message=message, source=source))
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def get(self, level: str | None = None, source: str | None = None,
            limit: int = 100) -> list[dict]:
        result = self.entries
        if level is not None:
            result = [e for e in result if e.level == level]
        if source is not None:
            result = [e for e in result if e.source == source]
        return [e.to_dict() for e in result[-limit:]]

    def clear(self) -> None:
        self.entries.clear()

    def count(self) -> int:
        return len(self.entries)
