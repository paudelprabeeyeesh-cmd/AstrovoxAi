"""
Coordinates integration steps with dependency resolution.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class StepStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class IntegrationStep:
    name: str
    fn: Callable[..., Any]
    dependencies: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    name: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None


class IntegrationCoordinator:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._steps: Dict[str, IntegrationStep] = {}
        self._results: Dict[str, StepResult] = {}

    def register(self, step: IntegrationStep) -> None:
        with self._lock:
            self._steps[step.name] = step

    def run(self) -> Dict[str, StepResult]:
        with self._lock:
            steps = dict(self._steps)
        results: Dict[str, StepResult] = dict(self._results)
        remaining = [name for name in steps if name not in results]
        changed = True
        while changed and remaining:
            changed = False
            next_remaining: List[str] = []
            for name in remaining:
                step = steps[name]
                deps_ok = all(dep in results and results[dep].status == StepStatus.COMPLETED for dep in step.dependencies)
                if not deps_ok:
                    next_remaining.append(name)
                    continue
                try:
                    output = step.fn(**step.params)
                    results[name] = StepResult(name=name, status=StepStatus.COMPLETED, output=output)
                    changed = True
                except Exception as _e:  # noqa: BLE001
                    results[name] = StepResult(name=name, status=StepStatus.FAILED, error=str(_e))
                    changed = True
            remaining = next_remaining
        for name in remaining:
            results[name] = StepResult(name=name, status=StepStatus.SKIPPED)
        with self._lock:
            self._results = results
        return dict(results)

    def results(self) -> Dict[str, StepResult]:
        with self._lock:
            return dict(self._results)
