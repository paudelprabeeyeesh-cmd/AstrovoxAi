"""Backup verification and integrity checks."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BackupManifest:
    backup_id: str
    database_name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    checksum: str = ""
    encryption_enabled: bool = False
    verified: bool = False
    verified_at: Optional[datetime] = None
    tables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BackupVerifier:
    def __init__(self):
        self._manifests: Dict[str, BackupManifest] = {}

    def register_backup(self, manifest: BackupManifest) -> None:
        self._manifests[manifest.backup_id] = manifest
        logger.info("Registered backup %s", manifest.backup_id)

    async def verify(self, backup_id: str, data: bytes) -> Dict[str, Any]:
        manifest = self._manifests.get(backup_id)
        if manifest is None:
            return {"status": "error", "message": "Unknown backup"}

        checksum = hashlib.sha256(data).hexdigest()
        integrity_ok = checksum == manifest.checksum if manifest.checksum else True
        size_ok = len(data) == manifest.size_bytes if manifest.size_bytes else True
        table_count_ok = True

        try:
            parsed = json.loads(data.decode("utf-8")) if data else {}
            table_count_ok = len(parsed.get("tables", [])) == len(manifest.tables)
        except Exception:
            table_count_ok = False

        status = "ok" if (integrity_ok and size_ok and table_count_ok) else "degraded"
        manifest.verified = status == "ok"
        manifest.verified_at = datetime.utcnow()
        logger.info("Backup %s verification: %s", backup_id, status)
        return {
            "status": status,
            "backup_id": backup_id,
            "integrity_ok": integrity_ok,
            "size_ok": size_ok,
            "table_count_ok": table_count_ok,
            "checksum": checksum,
        }

    async def restore_dry_run(self, backup_id: str) -> Dict[str, Any]:
        manifest = self._manifests.get(backup_id)
        if manifest is None:
            return {"status": "error", "message": "Unknown backup"}
        return {
            "status": "dry_run_ok",
            "tables_to_restore": manifest.tables,
            "estimated_time_seconds": len(manifest.tables) * 5,
        }

    def list_backups(self) -> List[Dict[str, Any]]:
        return [
            {
                "backup_id": m.backup_id,
                "database_name": m.database_name,
                "created_at": m.created_at.isoformat(),
                "size_bytes": m.size_bytes,
                "verified": m.verified,
                "tables": m.tables,
            }
            for m in self._manifests.values()
        ]
