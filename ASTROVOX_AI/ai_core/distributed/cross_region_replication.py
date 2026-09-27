"""Cross-region replication for KV cache and model state synchronization."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ASTROVOX_AI.ai_core.distributed._base import BackgroundService, validate_node_id

logger = logging.getLogger(__name__)


@dataclass
class ReplicationRecord:
    key: str
    value: Any
    version: int
    timestamp: float
    source_region: str
    checksum: str


class CrossRegionReplication(BackgroundService):
    def __init__(
        self,
        local_region: str,
        remote_regions: Optional[List[str]] = None,
        sync_interval: float = 5.0,
        consistency_model: str = "eventual",
    ):
        super().__init__(check_interval=sync_interval)
        validate_node_id(local_region)
        self.local_region = local_region
        self.remote_regions = list(remote_regions or [])
        self.consistency_model = consistency_model
        self._local_store: Dict[str, ReplicationRecord] = {}
        self._pending_writes: Dict[str, ReplicationRecord] = {}

    def put(self, key: str, value: Any) -> None:
        validate_node_id(key)
        checksum = self._compute_checksum(value)
        record = ReplicationRecord(
            key=key,
            value=value,
            version=self._get_next_version(key),
            timestamp=time.time(),
            source_region=self.local_region,
            checksum=checksum,
        )
        self._local_store[key] = record
        self._pending_writes[key] = record
        logger.debug("Queued replication for key %s", key)

    def get(self, key: str) -> Optional[Any]:
        validate_node_id(key)
        record = self._local_store.get(key)
        return record.value if record else None

    def _compute_checksum(self, value: Any) -> str:
        try:
            payload = json.dumps(value, sort_keys=True, default=str)
        except (TypeError, ValueError):
            payload = str(value)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _get_next_version(self, key: str) -> int:
        existing = self._local_store.get(key)
        return (existing.version + 1) if existing else 1

    def _tick(self) -> None:
        self._replicate_pending()
        self._pull_remote_changes()

    def _replicate_pending(self) -> None:
        for key, record in list(self._pending_writes.items()):
            for region in self.remote_regions:
                try:
                    self._push_to_region(region, record)
                except Exception:
                    logger.warning("Failed to replicate key %s to region %s", key, region)

    def _push_to_region(self, region: str, record: ReplicationRecord) -> None:
        logger.debug("Replicating key %s to region %s", record.key, region)

    def _pull_remote_changes(self) -> None:
        for region in self.remote_regions:
            try:
                changes = self._fetch_remote_changes(region)
                for key, remote_record in changes.items():
                    local = self._local_store.get(key)
                    if not local or remote_record.version > local.version:
                        self._local_store[key] = remote_record
            except Exception:
                logger.warning("Failed to pull changes from region %s", region)

    def _fetch_remote_changes(self, region: str) -> Dict[str, ReplicationRecord]:
        return {}

    def get_replication_status(self) -> Dict[str, Any]:
        return {
            "local_region": self.local_region,
            "remote_regions": self.remote_regions,
            "pending_writes": len(self._pending_writes),
            "local_entries": len(self._local_store),
            "consistency_model": self.consistency_model,
        }
