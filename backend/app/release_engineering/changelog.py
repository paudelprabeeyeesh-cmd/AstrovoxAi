"""Changelog generator for releases."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChangelogEntry:
    version: str
    date: datetime
    changes: List[str]
    author: str


class ChangelogGenerator:
    def __init__(self) -> None:
        self._entries: List[ChangelogEntry] = []

    def add_entry(self, entry: ChangelogEntry) -> None:
        self._entries.append(entry)

    def generate(self, version: str) -> str:
        lines = [f"## {version}"]
        for entry in self._entries:
            if entry.version == version:
                lines.extend(f"- {change}" for change in entry.changes)
        return "\n".join(lines)


changelog_generator = ChangelogGenerator()
