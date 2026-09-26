"""Chaos security engineering with fault injection and resilience testing."""
import hashlib
import logging
import random
import time
import threading
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ChaosAction(Enum):
    INJECT_DELAY = "inject_delay"
    INJECT_ERROR = "inject_error"
    INJECT_RESOURCE_EXHAUSTION = "inject_resource_exhaustion"
    INJECT_CORRUPTION = "inject_corruption"
    SIMULATE_FAILURE = "simulate_failure"


@dataclass
class ChaosExperiment:
    experiment_id: str
    action: ChaosAction
    target: str
    probability: float
    active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChaosSecurity:
    def __init__(self):
        self._experiments: Dict[str, ChaosExperiment] = {}
        self._results: List[Dict[str, Any]] = []
        self._lock = __import__('threading').Lock()
        self._enabled = False

    def register_experiment(self, experiment: ChaosExperiment):
        with self._lock:
            self._experiments[experiment.experiment_id] = experiment
        logger.info("Registered chaos experiment %s", experiment.experiment_id)

    def start(self, experiment_id: str):
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp:
                exp.active = True
                self._enabled = True

    def stop(self, experiment_id: str):
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp:
                exp.active = False

    def maybe_inject(self, target: str, original_fn: Callable, *args, **kwargs) -> Any:
        with self._lock:
            active = [e for e in self._experiments.values() if e.active and e.target == target]
        if not active or not self._enabled:
            return original_fn(*args, **kwargs)
        experiment = random.choice(active)
        if random.random() > experiment.probability:
            return original_fn(*args, **kwargs)
        result = self._apply(experiment, original_fn, *args, **kwargs)
        with self._lock:
            self._results.append({"experiment_id": experiment.experiment_id, "action": experiment.action.value, "target": target, "timestamp": time.time()})
        return result

    def _apply(self, experiment: ChaosExperiment, fn: Callable, *args, **kwargs) -> Any:
        if experiment.action == ChaosAction.INJECT_DELAY:
            time.sleep(experiment.metadata.get("delay_seconds", 1))
            return fn(*args, **kwargs)
        if experiment.action == ChaosAction.INJECT_ERROR:
            raise experiment.metadata.get("exception", RuntimeError("Chaos injected error"))
        if experiment.action == ChaosAction.INJECT_RESOURCE_EXHAUSTION:
            [bytearray(1024 * 1024) for _ in range(100)]
            return fn(*args, **kwargs)
        if experiment.action == ChaosAction.SIMULATE_FAILURE:
            logger.warning("Chaos: simulating failure for %s", experiment.target)
            return None
        return fn(*args, **kwargs)

    def get_report(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active_experiments": sum(1 for e in self._experiments.values() if e.active),
                "total_experiments": len(self._experiments),
                "injections": len(self._results),
                "enabled": self._enabled,
            }


chaos_security = ChaosSecurity()
