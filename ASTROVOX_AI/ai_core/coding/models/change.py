"""Change model for multi-file edits."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FileChange:
    path: str
    old_text: str
    new_text: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeSet:
    changes: list[FileChange] = field(default_factory=list)
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, change: FileChange) -> None:
        self.changes.append(change)
