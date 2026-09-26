"""Multi-file editor."""

from __future__ import annotations

import logging
import os
from typing import Any

from ASTROVOX_AI.ai_core.coding.models.change import ChangeSet, FileChange

logger = logging.getLogger(__name__)


class MultiFileEditor:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.changeset = ChangeSet()

    def edit(self, rel_path: str, old: str, new: str, description: str = "") -> dict[str, Any]:
        full = os.path.join(self.repo_path, rel_path)
        try:
            with open(full, "r", encoding="utf-8") as f:
                current = f.read()
        except Exception as exc:
            return {"file": rel_path, "error": str(exc)}
        if old not in current:
            return {"file": rel_path, "error": "old text not found", "applied": False}
        updated = current.replace(old, new, 1)
        self.changeset.add(FileChange(path=rel_path, old_text=old, new_text=new, description=description))
        return {"file": rel_path, "applied": True}

    def batch_edit(self, edits: list[dict[str, str]]) -> dict[str, Any]:
        results = []
        for e in edits:
            results.append(self.edit(e.get("path", ""), e.get("old", ""), e.get("new", ""), e.get("description", "")))
        return {"edits": len(edits), "results": results}

    def preview(self) -> dict[str, Any]:
        return {
            "summary": self.changeset.summary,
            "changes": [
                {"path": c.path, "description": c.description} for c in self.changeset.changes
            ],
        }

    def commit(self) -> dict[str, Any]:
        written = []
        for change in self.changeset.changes:
            full = os.path.join(self.repo_path, change.path)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    current = f.read()
                updated = current.replace(change.old_text, change.new_text, 1)
                with open(full, "w", encoding="utf-8") as f:
                    f.write(updated)
                written.append(change.path)
            except Exception as exc:
                logger.debug("commit failed for %s: %s", change.path, exc)
        count = len(written)
        self.changeset = ChangeSet()
        return {"written": written, "count": count}

    def rollback(self) -> dict[str, Any]:
        self.changeset = ChangeSet()
        return {"rolled_back": True}
