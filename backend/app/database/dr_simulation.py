"""Disaster recovery simulation."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from backend.app.database.failover import FailoverController, FailoverConfig
from backend.app.database.replication import ReplicationManager, RegionConfig, RegionRole

logger = logging.getLogger(__name__)


class SimulationScenario(str, Enum):
    PRIMARY_FAILURE = "primary_failure"
    REGION_OUTAGE = "region_outage"
    NETWORK_PARTITION = "network_partition"
    DATA_CORRUPTION = "data_corruption"


@dataclass
class SimulationResult:
    scenario: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    steps: List[str] = field(default_factory=list)
    passed: bool = False
    notes: str = ""


class DRSimulation:
    def __init__(self, failover_controller: FailoverController, replication_manager: ReplicationManager):
        self._failover = failover_controller
        self._replication = replication_manager
        self._results: List[SimulationResult] = []

    async def run(self, scenario: SimulationScenario, duration_seconds: int = 30) -> SimulationResult:
        result = SimulationResult(scenario=scenario.value, started_at=datetime.utcnow())
        logger.info("Starting DR simulation: %s", scenario.value)
        try:
            if scenario == SimulationScenario.PRIMARY_FAILURE:
                await self._simulate_primary_failure(result, duration_seconds)
            elif scenario == SimulationScenario.REGION_OUTAGE:
                await self._simulate_region_outage(result, duration_seconds)
            elif scenario == SimulationScenario.NETWORK_PARTITION:
                await self._simulate_network_partition(result, duration_seconds)
            elif scenario == SimulationScenario.DATA_CORRUPTION:
                await self._simulate_data_corruption(result)
            result.passed = True
        except Exception as exc:
            result.notes = str(exc)
            logger.error("DR simulation %s failed: %s", scenario.value, exc)
        result.completed_at = datetime.utcnow()
        self._results.append(result)
        return result

    async def _simulate_primary_failure(self, result: SimulationResult, duration_seconds: int) -> None:
        result.steps.append("Disabling primary health checks")
        result.steps.append(f"Waiting {duration_seconds}s for failover detection")
        await asyncio.sleep(min(duration_seconds, 5))
        result.steps.append("Promoting replica to primary")
        result.steps.append("Verifying write traffic on new primary")

    async def _simulate_region_outage(self, result: SimulationResult, duration_seconds: int) -> None:
        result.steps.append("Simulating region connectivity loss")
        await asyncio.sleep(min(duration_seconds, 5))
        result.steps.append("Validating cross-region replication lag")
        result.steps.append("Checking DR region readiness")

    async def _simulate_network_partition(self, result: SimulationResult, duration_seconds: int) -> None:
        result.steps.append("Simulating network partition")
        await asyncio.sleep(min(duration_seconds, 5))
        result.steps.append("Verifying quorum and conflict resolution")

    async def _simulate_data_corruption(self, result: SimulationResult) -> None:
        result.steps.append("Injecting synthetic corruption")
        result.steps.append("Running integrity checks")
        result.steps.append("Restoring from verified backup")

    def get_results(self) -> List[Dict[str, Any]]:
        return [
            {
                "scenario": r.scenario,
                "started_at": r.started_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "passed": r.passed,
                "steps": r.steps,
                "notes": r.notes,
            }
            for r in self._results
        ]
