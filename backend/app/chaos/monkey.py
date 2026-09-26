"""Chaos monkey for resilience testing."""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChaosAction(Enum):
    KILL_PROCESS = "kill_process"
    INJECT_LATENCY = "inject_latency"
    DROP_PACKETS = "drop_packets"
    FILL_DISK = "fill_disk"
    EAT_MEMORY = "eat_memory"
    RAISE_EXCEPTION = "raise_exception"


@dataclass
class ChaosExperiment:
    experiment_id: str
    name: str
    action: ChaosAction
    target: str
    probability: float = 0.1
    duration_seconds: float = 10.0
    payload: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChaosResult:
    experiment_id: str
    executed_at: datetime
    action: ChaosAction
    success: bool
    error: Optional[str] = None


class ChaosMonkey:
    def __init__(self) -> None:
        self._experiments: Dict[str, ChaosExperiment] = {}
        self._results: List[ChaosResult] = []
        self._running: bool = False
        self._scheduler_task: Optional[asyncio.Task] = None

    def add_experiment(self, experiment: ChaosExperiment) -> None:
        self._experiments[experiment.experiment_id] = experiment
        logger.info("Registered chaos experiment %s: %s", experiment.experiment_id, experiment.name)

    def remove_experiment(self, experiment_id: str) -> None:
        self._experiments.pop(experiment_id, None)

    async def run_experiment(self, experiment_id: str) -> ChaosResult:
        experiment = self._experiments.get(experiment_id)
        if not experiment or not experiment.enabled:
            raise ValueError(f"Unknown or disabled experiment: {experiment_id}")
        logger.warning("Running chaos experiment %s on %s", experiment_id, experiment.target)
        start = datetime.now(timezone.utc)
        try:
            await self._inject(experiment)
            success = True
            error = None
        except Exception as exc:
            success = False
            error = str(exc)
            logger.exception("Chaos experiment %s failed", experiment_id)
        result = ChaosResult(
            experiment_id=experiment_id,
            executed_at=start,
            action=experiment.action,
            success=success,
            error=error,
        )
        self._results.append(result)
        return result

    async def _inject(self, experiment: ChaosExperiment) -> None:
        action = experiment.action
        if action == ChaosAction.INJECT_LATENCY:
            delay = experiment.payload.get("delay_ms", 1000) / 1000.0
            await asyncio.sleep(delay)
        elif action == ChaosAction.RAISE_EXCEPTION:
            raise RuntimeError(experiment.payload.get("message", "Chaos error"))
        elif action == ChaosAction.DROP_PACKETS:
            await asyncio.sleep(experiment.duration_seconds)
        elif action == ChaosAction.EAT_MEMORY:
            data = bytearray(experiment.payload.get("bytes", 1024 * 1024))
            await asyncio.sleep(experiment.duration_seconds)
            del data
        else:
            logger.info("Simulated chaos action %s on %s", action.value, experiment.target)

    async def start_scheduler(self, interval_seconds: float = 60.0) -> None:
        self._running = True
        while self._running:
            enabled = [e for e in self._experiments.values() if e.enabled]
            if enabled and random.random() < 0.3:
                experiment = random.choice(enabled)
                try:
                    await self.run_experiment(experiment.experiment_id)
                except Exception:
                    logger.exception("Scheduled chaos experiment failed")
            await asyncio.sleep(interval_seconds)

    def stop_scheduler(self) -> None:
        self._running = False

    @property
    def results(self) -> List[ChaosResult]:
        return list(self._results)


chaos_monkey = ChaosMonkey()
