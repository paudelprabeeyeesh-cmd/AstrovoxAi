"""
Final data pipeline with ETL stages.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class ETLJob:
    name: str
    extract: Callable[..., Any]
    transform: Callable[..., Any]
    load: Callable[..., Any]
    extract_params: Dict[str, Any] = field(default_factory=dict)
    transform_params: Dict[str, Any] = field(default_factory=dict)
    load_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    job_name: str
    extracted: Any = None
    transformed: Any = None
    loaded: Any = None
    success: bool = False
    error: Optional[str] = None


class DataPipeline:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: Dict[str, ETLJob] = {}
        self._results: Dict[str, PipelineResult] = {}

    def register(self, job: ETLJob) -> None:
        with self._lock:
            self._jobs[job.name] = job

    def run(self, name: str) -> PipelineResult:
        with self._lock:
            job = self._jobs.get(name)
        if not job:
            result = PipelineResult(job_name=name, error="job not found")
            with self._lock:
                self._results[name] = result
            return result
        try:
            extracted = job.extract(**job.extract_params)
            transformed = job.transform(extracted, **job.transform_params)
            loaded = job.load(transformed, **job.load_params)
            result = PipelineResult(job_name=name, extracted=extracted, transformed=transformed, loaded=loaded, success=True)
        except Exception as _e:  # noqa: BLE001
            result = PipelineResult(job_name=name, error=str(_e))
        with self._lock:
            self._results[name] = result
        return result

    def result(self, name: str) -> Optional[PipelineResult]:
        with self._lock:
            return self._results.get(name)
