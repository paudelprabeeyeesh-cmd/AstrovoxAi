"""
release_notes_generator - product_polish

Generate structured release notes from commit messages, feature tags,
and manual entries.
"""

from __future__ import annotations

import copy
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReleaseNoteEntry:
    id: str
    version: str
    title: str
    description: str
    entry_type: str = "feature"
    tags: List[str] = field(default_factory=list)
    source: str = "manual"
    author: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "title": self.title,
            "description": self.description,
            "entry_type": self.entry_type,
            "tags": self.tags,
            "source": self.source,
            "author": self.author,
            "created_at": self.created_at,
        }


class ReleaseNotesGenerator:
    TYPE_ALIASES = {
        "feat": "feature",
        "feature": "feature",
        "fix": "bugfix",
        "bugfix": "bugfix",
        "fixbug": "bugfix",
        "hotfix": "bugfix",
        "perf": "improvement",
        "improvement": "improvement",
        "refactor": "refactor",
        "docs": "documentation",
        "documentation": "documentation",
        "dep": "breaking",
        "breaking": "breaking",
        "chore": "maintenance",
        "maintenance": "maintenance",
        "security": "security",
    }

    def __init__(self):
        self._entries: Dict[str, ReleaseNoteEntry] = {}
        self._lock = threading.Lock()

    def _normalize_entry_type(self, raw: str) -> str:
        return self.TYPE_ALIASES.get(raw.strip().lower(), "feature")

    def add_entry(
        self,
        version: str,
        title: str,
        description: str,
        entry_type: str = "feature",
        tags: Optional[List[str]] = None,
        source: str = "manual",
        author: str = "",
    ) -> ReleaseNoteEntry:
        import uuid
        entry_id = str(uuid.uuid4())
        normalized_type = self._normalize_entry_type(entry_type)
        entry = ReleaseNoteEntry(
            id=entry_id,
            version=version,
            title=title,
            description=description,
            entry_type=normalized_type,
            tags=tags or [],
            source=source,
            author=author,
        )
        with self._lock:
            self._entries[entry_id] = entry
        logger.info("Added release note entry %s for version %s", entry_id, version)
        return entry

    def get_entry(self, entry_id: str) -> Optional[ReleaseNoteEntry]:
        with self._lock:
            return self._entries.get(entry_id)

    def list_entries(self, version: Optional[str] = None) -> List[ReleaseNoteEntry]:
        with self._lock:
            entries = list(self._entries.values())
        if version is not None:
            entries = [e for e in entries if e.version == version]
        return sorted(entries, key=lambda e: (e.version, e.created_at))

    def parse_commit_message(self, version: str, message: str, author: str = "") -> List[ReleaseNoteEntry]:
        pattern = re.compile(r"^(?P<type>\w+)(\((?P<scope>[^)]+)\))?\s*:\s*(?P<description>.+)$", re.MULTILINE)
        entries: List[ReleaseNoteEntry] = []
        for match in pattern.finditer(message):
            raw_type = match.group("type")
            scope = match.group("scope") or ""
            description = match.group("description").strip()
            title = f"[{raw_type}] {description}"
            if scope:
                title = f"[{raw_type}][{scope}] {description}"
            entry = self.add_entry(
                version=version,
                title=title,
                description=description,
                entry_type=raw_type,
                source="commit",
                author=author,
            )
            entries.append(entry)
        return entries

    def generate_notes(self, version: str, group_by_type: bool = True) -> str:
        entries = self.list_entries(version)
        if not entries:
            return f"# Release Notes {version}\n\nNo entries for this version.\n"
        lines = [f"# Release Notes {version}", ""]
        if group_by_type:
            grouped: Dict[str, List[ReleaseNoteEntry]] = {}
            for entry in entries:
                grouped.setdefault(entry.entry_type, []).append(entry)
            for entry_type, group in grouped.items():
                lines.append(f"## {entry_type.title()}")
                lines.append("")
                for entry in group:
                    lines.append(f"- {entry.title}: {entry.description}")
                lines.append("")
        else:
            for entry in entries:
                lines.append(f"- [{entry.entry_type}] {entry.title}: {entry.description}")
            lines.append("")
        return "\n".join(lines)

    def markdown(self, version: str) -> str:
        return self.generate_notes(version, group_by_type=True)
