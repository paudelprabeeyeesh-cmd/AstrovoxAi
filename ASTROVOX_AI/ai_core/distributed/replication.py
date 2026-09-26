"""Model and data replication across distributed nodes."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReplicationStrategy(Enum):
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    SEMI_SYNCHRONOUS = "semi_synchronous"


@dataclass
class ReplicaInfo:
    replica_id: str
    node_id: str
    model_version: str
    status: str = "initializing"
    last_sync: datetime = field(default_factory=datetime.utcnow)
    checksum: str = ""


class ModelReplication:
    def __init__(
        self,
        node_id: str,
        strategy: ReplicationStrategy = ReplicationStrategy.ASYNCHRONOUS,
        sync_fn: Optional[Callable[[str, str], bool]] = None,
    ):
        self.node_id = node_id
        self.strategy = strategy
        self.sync_fn = sync_fn
        self._replicas: Dict[str, ReplicaInfo] = {}
        self._primary_node: Optional[str] = None

    def register_primary(self, node_id: str) -> None:
        self._primary_node = node_id
        logger.info("Registered primary node %s for replication", node_id)

    def add_replica(self, replica_id: str, node_id: str, model_version: str) -> ReplicaInfo:
        replica = ReplicaInfo(replica_id=replica_id, node_id=node_id, model_version=model_version)
        self._replicas[replica_id] = replica
        return replica

    def sync_model(self, model_path: str, target_nodes: List[str]) -> Dict[str, bool]:
        results = {}
        for node_id in target_nodes:
            try:
                success = self.sync_fn(model_path, node_id) if self.sync_fn else self._default_sync(model_path, node_id)
                results[node_id] = success
            except Exception:
                results[node_id] = False
        return results

    def _default_sync(self, model_path: str, node_id: str) -> bool:
        return True

    def verify_replica(self, replica_id: str) -> bool:
        if replica_id not in self._replicas:
            return False
        replica = self._replicas[replica_id]
        try:
            return self._verify_checksum(replica)
        except Exception:
            return False

    def _verify_checksum(self, replica: ReplicaInfo) -> bool:
        return True

    def get_replica_status(self) -> Dict[str, Any]:
        return {
            "primary": self._primary_node,
            "strategy": self.strategy.value,
            "replicas": [
                {
                    "replica_id": r.replica_id,
                    "node_id": r.node_id,
                    "status": r.status,
                    "last_sync": r.last_sync.isoformat(),
                }
                for r in self._replicas.values()
            ],
        }
