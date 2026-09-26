"""Read/write splitting with automatic routing."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.app.database.abstraction import BaseDatabase, DatabaseConfig, DatabaseRegistry, DatabaseType, MultiDatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class ReplicaConfig:
    host: str
    port: int
    weight: float = 1.0
    lag: float = 0.0
    healthy: bool = True


@dataclass
class RoutingStats:
    reads_primary: int = 0
    reads_replica: int = 0
    writes: int = 0
    failover_count: int = 0


class ReadWriteSplitter:
    def __init__(
        self,
        manager: MultiDatabaseManager,
        primary_name: str,
        replica_names: Optional[list[str]] = None,
        mode: str = "auto",
        max_replica_lag: float = 5.0,
    ):
        self.manager = manager
        self.primary_name = primary_name
        self.replica_names = replica_names or []
        self.mode = mode
        self.max_replica_lag = max_replica_lag
        self.stats = RoutingStats()
        self._replicas: Dict[str, ReplicaConfig] = {}

    def register_replica(self, name: str, config: ReplicaConfig) -> None:
        self._replicas[name] = config

    def _should_use_replica(self) -> bool:
        if self.mode == "primary_only":
            return False
        if self.mode == "replica_only":
            return True
        healthy_replicas = [r for r in self._replicas.values() if r.healthy and r.lag <= self.max_replica_lag]
        return bool(healthy_replicas)

    def _select_replica(self) -> str:
        candidates = [name for name, r in self._replicas.items() if r.healthy and r.lag <= self.max_replica_lag]
        if not candidates:
            return self.primary_name
        total = sum(self._replicas[name].weight for name in candidates)
        r = random.uniform(0, total)
        upto = 0.0
        for name in candidates:
            upto += self._replicas[name].weight
            if upto >= r:
                return name
        return candidates[-1]

    async def execute_read(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if not self._should_use_replica():
            self.stats.reads_primary += 1
            return await self.manager.execute_on(self.primary_name, query, params)
        replica = self._select_replica()
        if replica == self.primary_name:
            self.stats.reads_primary += 1
        else:
            self.stats.reads_replica += 1
        return await self.manager.execute_on(replica, query, params)

    async def execute_write(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        self.stats.writes += 1
        return await self.manager.execute_on(self.primary_name, query, params)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "reads_primary": self.stats.reads_primary,
            "reads_replica": self.stats.reads_replica,
            "writes": self.stats.writes,
            "failover_count": self.stats.failover_count,
            "replicas": {
                name: {"healthy": r.healthy, "lag": r.lag, "weight": r.weight}
                for name, r in self._replicas.items()
            },
        }
