"""
Workflow automation with pipelines and stages.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class StageStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class StageResult:
    name: str
    status: StageStatus
    output: Any = None
    error: Optional[str] = None


StageFn = Callable[..., Any]


@dataclass
class Stage:
    name: str
    fn: StageFn
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[Callable[..., bool]] = None


@dataclass
class Pipeline:
    name: str
    stages: List[Stage]


class WorkflowEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pipelines: Dict[str, Pipeline] = {}
        self._results: Dict[str, Dict[str, StageResult]] = {}

    def register(self, pipeline: Pipeline) -> None:
        with self._lock:
            self._pipelines[pipeline.name] = pipeline

    def run(self, name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, StageResult]:
        with self._lock:
            pipeline = self._pipelines.get(name)
        if not pipeline:
            raise KeyError(f"pipeline not found: {name}")
        results: Dict[str, StageResult] = {}
        for stage in pipeline.stages:
            if stage.condition and not stage.condition():
                results[stage.name] = StageResult(name=stage.name, status=StageStatus.SKIPPED)
                continue
            try:
                output = stage.fn(**dict(stage.params, name=stage.name))
                results[stage.name] = StageResult(name=stage.name, status=StageStatus.COMPLETED, output=output)
            except Exception as _e:  # noqa: BLE001
                results[stage.name] = StageResult(name=stage.name, status=StageStatus.FAILED, error=str(_e))
                break
        with self._lock:
            self._results[name] = results
        return dict(results)

    def results(self, name: str) -> Dict[str, StageResult]:
        with self._lock:
            return dict(self._results.get(name, {}))
