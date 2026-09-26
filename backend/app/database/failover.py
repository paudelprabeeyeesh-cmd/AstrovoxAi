"""Auto-failover with health checks and promotion."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.app.database.abstraction import BaseDatabase, DatabaseConfig, MultiDatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class FailoverConfig:
    health_check_interval: float = 10.0
    health_check_timeout: float = 5.0
    failover_threshold: int = 3
    promote_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff: float = 60.0


@dataclass
class NodeState:
    name: str
    healthy: bool = True
    consecutive_failures: int = 0
    last_check: float = 0.0
    promoted: bool = False


class FailoverController:
    def __init__(
        self,
        manager: MultiDatabaseManager,
        primary_name: str,
        replica_names: Optional[list[str]] = None,
        config: Optional[FailoverConfig] = None,
    ):
        self.manager = manager
        self.primary_name = primary_name
        self.replica_names = replica_names or []
        self.config = config or FailoverConfig()
        self._states: Dict[str, NodeState] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        for name in [self.primary_name] + self.replica_names:
            self._states[name] = NodeState(name=name)
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Failover controller started")

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Failover controller stopped")

    async def _monitor_loop(self) -> None:
        while self._running:
            await self._check_nodes()
            await asyncio.sleep(self.config.health_check_interval)

    async def _check_nodes(self) -> None:
        for name, state in self._states.items():
            try:
                db = self.manager.get_database(name)
                healthy = await asyncio.wait_for(db.health_check(), timeout=self.config.health_check_timeout)
                state.healthy = healthy
                state.consecutive_failures = 0 if healthy else state.consecutive_failures + 1
            except asyncio.TimeoutError:
                state.healthy = False
                state.consecutive_failures += 1
            state.last_check = asyncio.get_event_loop().time()

            if not state.healthy and state.consecutive_failures >= self.config.failover_threshold and not state.promoted:
                await self._promote_replica_for(name)

    async def _promote_replica_for(self, failed_primary: str) -> None:
        for replica_name in self.replica_names:
            try:
                db = self.manager.get_database(replica_name)
                if await db.health_check():
                    logger.info("Promoting %s to primary", replica_name)
                    self.primary_name, self.replica_names = replica_name, [
                        r for r in self.replica_names if r != replica_name
                    ] + [failed_primary]
                    self._states[failed_primary].promoted = True
                    self._states[failed_primary].healthy = False
                    self._states[replica_name].promoted = True
                    self._states[replica_name].healthy = True
                    break
            except Exception:
                continue
        else:
            logger.critical("No healthy replica available for failover")

    def get_status(self) -> Dict[str, Any]:
        return {
            "primary": self.primary_name,
            "replicas": self.replica_names,
            "nodes": {
                name: {
                    "healthy": s.healthy,
                    "consecutive_failures": s.consecutive_failures,
                    "last_check": s.last_check,
                    "promoted": s.promoted,
                }
                for name, s in self._states.items()
            },
        }
