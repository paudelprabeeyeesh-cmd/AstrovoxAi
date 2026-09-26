"""Multi-file editor."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class MultiFileEditor:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self._changes: dict[str, str] = {}
        self._backups: dict[str, str] = {}

    def edit(self, rel_path: str, old: str, new: str) -> dict[str, Any]:
        full = os.path.join(self.repo_path, rel_path)
        try:
            with open(full, "r", encoding="utf-8") as f:
                current = f.read()
        except Exception as exc:
            return {"file": rel_path, "error": str(exc)}
        if old not in current:
            return {"file": rel_path, "error": "old text not found", "applied": False}
        if rel_path not in self._backups:
            self._backups[rel_path] = current
        updated = current.replace(old, new, 1)
        self._changes[rel_path] = updated
        return {"file": rel_path, "applied": True, "replacement_count": 1}

    def batch_edit(self, edits: list[dict[str, str]]) -> dict[str, Any]:
        results = []
        for e in edits:
            results.append(self.edit(e.get("path", ""), e.get("old", ""), e.get("new", "")))
        return {"edits": len(edits), "results": results}

    def preview(self, rel_path: str) -> dict[str, Any] | None:
        content = self._changes.get(rel_path)
        if content is None:
            return None
        return {"path": rel_path, "preview": content}

    def commit(self) -> dict[str, Any]:
        written = []
        for rel, content in self._changes.items():
            full = os.path.join(self.repo_path, rel)
            try:
                with open(full, "w", encoding="utf-8") as f:
                    f.write(content)
                written.append(rel)
            except Exception as exc:
                logger.debug("commit failed for %s: %s", rel, exc)
        self._changes.clear()
        return {"written": written}

    def rollback(self) -> dict[str, Any]:
        restored = []
        for rel, backup in self._backups.items():
            full = os.path.join(self.repo_path, rel)
            try:
                with open(full, "w", encoding="utf-8") as f:
                    f.write(backup)
                restored.append(rel)
            except Exception as exc:
                logger.debug("rollback failed for %s: %s", rel, exc)
        self._changes.clear()
        self._backups.clear()
        return {"restored": restored}
