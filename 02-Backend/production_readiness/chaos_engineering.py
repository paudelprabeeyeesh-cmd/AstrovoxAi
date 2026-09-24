"""Chaos engineering: fault injection and resilience testing."""
from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChaosExperiment:
    id: str
    name: str
    target: str
    fault_type: str
    duration_seconds: float
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    started: float = 0.0
    completed: float = 0.0
    result: Dict[str, Any] = field(default_factory=dict)


class ChaosRegistry:
    def __init__(self) -> None:
        self._experiments: Dict[str, ChaosExperiment] = {}
        self._lock = threading.Lock()

    def register(self, experiment: ChaosExperiment) -> None:
        with self._lock:
            self._experiments[experiment.id] = experiment

    def get(self, experiment_id: str) -> Optional[ChaosExperiment]:
        with self._lock:
            return self._experiments.get(experiment_id)

    def list(self) -> List[ChaosExperiment]:
        with self._lock:
            return list(self._experiments.values())


class ChaosEngineer:
    def __init__(self) -> None:
        self._experiments = ChaosRegistry()
        self._faults: Dict[str, Callable[..., Any]] = {}
        self._lock = threading.Lock()

    def register_fault(self, fault_type: str, func: Callable[..., Any]) -> None:
        with self._lock:
            self._faults[fault_type] = func

    def create_experiment(self, name: str, target: str, fault_type: str, duration_seconds: float, params: Optional[Dict[str, Any]] = None) -> ChaosExperiment:
        experiment = ChaosExperiment(
            id=f"chaos-{int(time.time() * 1000)}-{random.randint(1000, 9999)}",
            name=name,
            target=target,
            fault_type=fault_type,
            duration_seconds=duration_seconds,
            params=params or {},
        )
        self._experiments.register(experiment)
        logger.info("created experiment %s: %s on %s", experiment.id, name, target)
        return experiment

    def _inject_fault(self, experiment: ChaosExperiment, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        fault_func = self._faults.get(experiment.fault_type)
        if fault_func is None:
            logger.warning("fault type %s not registered", experiment.fault_type)
            return func(*args, **kwargs)
        return fault_func(func, experiment.params, *args, **kwargs)

    def run_experiment(self, experiment_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            raise ValueError(f"unknown experiment {experiment_id}")
        experiment.status = "running"
        experiment.started = time.time()
        start = time.time()
        try:
            result = self._inject_fault(experiment, func, *args, **kwargs)
            experiment.status = "completed"
            experiment.completed = time.time()
            experiment.result = {"success": True, "duration": experiment.completed - experiment.started}
            return result
        except Exception as exc:
            experiment.status = "failed"
            experiment.completed = time.time()
            experiment.result = {"success": False, "error": str(exc), "duration": experiment.completed - experiment.started}
            raise exc

    def resilience_test(self, func: Callable[..., Any], iterations: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        results = []
        for _ in range(iterations):
            experiment = self.create_experiment(name="resilience-test", target="system", fault_type="latency", duration_seconds=1.0, params={"ms": 50})
            try:
                result = self.run_experiment(experiment.id, func, *args, **kwargs)
                results.append({"status": "success", "result": result})
            except Exception as exc:
                results.append({"status": "failed", "error": str(exc)})
        passed = sum(1 for r in results if r["status"] == "success")
        return {"total": len(results), "passed": passed, "resilience": passed / max(len(results), 1), "results": results}

    def list_experiments(self) -> List[ChaosExperiment]:
        return self._experiments.list()
