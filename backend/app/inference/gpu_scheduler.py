"""GPU scheduling and resource management for inference workloads."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class GPUState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DRAINING = "draining"


@dataclass
class GPUJob:
    job_id: str
    gpu_id: int
    node_id: str
    model_id: str
    priority: int = 0
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"


class GPUScheduler:
    def __init__(self, gpu_capacity: int = 8, memory_per_gpu: int = 80_000):
        self.gpu_capacity = gpu_capacity
        self.memory_per_gpu = memory_per_gpu
        self._gpu_states: Dict[int, GPUState] = {i: GPUState.IDLE for i in range(gpu_capacity)}
        self._gpu_memory: Dict[int, int] = {i: memory_per_gpu for i in range(gpu_capacity)}
        self._job_queue: List[GPUJob] = []
        self._running_jobs: Dict[str, GPUJob] = {}
        self._job_counter = 0

    def submit_job(self, node_id: str, model_id: str, gpu_ids: List[int], priority: int = 0) -> List[str]:
        job_ids = []
        for gpu_id in gpu_ids:
            if gpu_id >= self.gpu_capacity or self._gpu_states[gpu_id] == GPUState.DRAINING:
                continue
            job_id = f"job_{self._job_counter:06d}"
            self._job_counter += 1
            job = GPUJob(job_id=job_id, gpu_id=gpu_id, node_id=node_id, model_id=model_id, priority=priority)
            self._job_queue.append(job)
            job_ids.append(job_id)
        self._schedule_pending()
        return job_ids

    def _schedule_pending(self) -> None:
        self._job_queue.sort(key=lambda j: -j.priority)
        remaining = []
        for job in self._job_queue:
            if self._gpu_states[job.gpu_id] == GPUState.IDLE:
                self._gpu_states[job.gpu_id] = GPUState.RUNNING
                job.status = "running"
                job.started_at = datetime.utcnow()
                self._running_jobs[job.job_id] = job
                logger.info("Scheduled job %s on GPU %d", job.job_id, job.gpu_id)
            else:
                remaining.append(job)
        self._job_queue = remaining

    def complete_job(self, job_id: str) -> None:
        if job_id not in self._running_jobs:
            return
        job = self._running_jobs.pop(job_id)
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        self._gpu_states[job.gpu_id] = GPUState.IDLE
        logger.info("Completed job %s on GPU %d", job.job_id, job.gpu_id)
        self._schedule_pending()

    def fail_job(self, job_id: str, error: str = "") -> None:
        if job_id not in self._running_jobs:
            return
        job = self._running_jobs.pop(job_id)
        job.status = "failed"
        job.completed_at = datetime.utcnow()
        self._gpu_states[job.gpu_id] = GPUState.ERROR
        logger.error("Job %s failed on GPU %d: %s", job.job_id, job.gpu_id, error)

    def drain_gpu(self, gpu_id: int) -> None:
        if gpu_id >= self.gpu_capacity:
            return
        self._gpu_states[gpu_id] = GPUState.DRAINING
        draining_jobs = [j for j in self._running_jobs.values() if j.gpu_id == gpu_id]
        for job in draining_jobs:
            self.fail_job(job.job_id, "GPU draining")

    def get_available_gpus(self) -> List[int]:
        return [i for i, s in self._gpu_states.items() if s == GPUState.IDLE]

    def get_gpu_status(self) -> Dict[str, Any]:
        return {
            "gpu_capacity": self.gpu_capacity,
            "available": len(self.get_available_gpus()),
            "running": sum(1 for s in self._gpu_states.values() if s == GPUState.RUNNING),
            "error": sum(1 for s in self._gpu_states.values() if s == GPUState.ERROR),
            "draining": sum(1 for s in self._gpu_states.values() if s == GPUState.DRAINING),
            "pending_jobs": len(self._job_queue),
        }

    def get_memory_usage(self, gpu_id: int) -> Tuple[int, int]:
        return self._gpu_memory.get(gpu_id, 0), self.memory_per_gpu
