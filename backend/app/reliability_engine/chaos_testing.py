"""Chaos testing and fault injection framework."""
from __future__ import annotations

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class FaultType(Enum):
    LATENCY = "latency"
    ERROR = "error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CRASH = "crash"
    NETWORK_PARTITION = "network_partition"


@dataclass
class ChaosExperiment:
    experiment_id: str
    name: str
    fault_type: FaultType
    target_service: str
    duration_seconds: int
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ExperimentStatus = ExperimentStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


class FaultInjector(ABC):
    @abstractmethod
    async def inject(self, experiment: ChaosExperiment) -> None:
        ...

    @abstractmethod
    async def revert(self, experiment: ChaosExperiment) -> None:
        ...


class LatencyInjector(FaultInjector):
    async def inject(self, experiment: ChaosExperiment) -> None:
        delay = experiment.parameters.get("delay_ms", 1000)
        logger.info("Injecting latency of %dms into %s", delay, experiment.target_service)
        await asyncio.sleep(delay / 1000)

    async def revert(self, experiment: ChaosExperiment) -> None:
        pass


class ErrorInjector(FaultInjector):
    async def inject(self, experiment: ChaosExperiment) -> None:
        error_rate = experiment.parameters.get("error_rate", 0.5)
        logger.info("Injecting errors with rate %.2f into %s", error_rate, experiment.target_service)

    async def revert(self, experiment: ChaosExperiment) -> None:
        pass


class ChaosEngine:
    def __init__(self) -> None:
        self._injectors: Dict[FaultType, FaultInjector] = {
            FaultType.LATENCY: LatencyInjector(),
            FaultType.ERROR: ErrorInjector(),
        }
        self._active_experiments: Dict[str, ChaosExperiment] = {}

    async def run_experiment(self, experiment: ChaosExperiment) -> ChaosExperiment:
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now(timezone.utc)
        injector = self._injectors.get(experiment.fault_type)
        if not injector:
            raise ValueError(f"No injector for fault type: {experiment.fault_type}")
        try:
            await asyncio.wait_for(
                injector.inject(experiment),
                timeout=experiment.duration_seconds,
            )
            experiment.status = ExperimentStatus.COMPLETED
            experiment.result = {"outcome": "success"}
        except Exception as exc:  # pragma: no cover
            experiment.status = ExperimentStatus.FAILED
            experiment.result = {"error": str(exc)}
        finally:
            experiment.completed_at = datetime.now(timezone.utc)
            await injector.revert(experiment)
        self._active_experiments[experiment.experiment_id] = experiment
        return experiment


chaos_engine = ChaosEngine()
