"""AI changelog generator."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIChangelogEntry:
    version: str
    date: datetime
    changes: List[str]
    author: str


class AIChangelogGenerator:
    def __init__(self) -> None:
        self._entries: List[AIChangelogEntry] = []

    def add_entry(self, entry: AIChangelogEntry) -> None:
        self._entries.append(entry)

    def generate(self, version: str) -> str:
        lines = [f"## {version}"]
        for entry in self._entries:
            if entry.version == version:
                lines.extend(f"- {change}" for change in entry.changes)
        return "\n".join(lines)


ai_changelog_generator = AIChangelogGenerator()
