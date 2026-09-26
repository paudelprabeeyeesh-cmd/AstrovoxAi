"""Code snapshot repository for versioning code states."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class SnapshotRepository:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.snapshots: list[dict[str, Any]] = []

    def create_snapshot(self, label: str = "", files: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if files is None:
            files = []
        snapshot = {
            "id": hashlib.sha256(f"{datetime.now(timezone.utc).isoformat()}{label}".encode()).hexdigest()[:16],
            "label": label,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": files,
            "file_count": len(files),
        }
        self.snapshots.append(snapshot)
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        for snap in self.snapshots:
            if snap["id"] == snapshot_id:
                return snap
        return None

    def list_snapshots(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.snapshots[-limit:]

    def diff_snapshots(self, snapshot_a: str, snapshot_b: str) -> dict[str, Any]:
        a = self.get_snapshot(snapshot_a)
        b = self.get_snapshot(snapshot_b)
        if not a or not b:
            return {"error": "snapshot not found"}
        return {"from": a, "to": b, "files_added": [], "files_removed": [], "files_changed": []}
