"""Cluster scheduling: GPU allocation and job management across nodes."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ClusterNode:
    node_id: int
    hostname: str
    gpu_ids: List[int]
    total_memory: int = 0
    available_memory: int = 0
    status: str = "healthy"


@dataclass
class ClusterJob:
    job_id: str
    num_gpus: int = 1
    priority: int = 0
    required_memory: int = 0
    fn: Optional[Any] = None
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    assigned_node: Optional[int] = None
    assigned_gpus: List[int] = field(default_factory=list)
    result: Any = None
    error: Optional[str] = None
    submitted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ClusterScheduler:
    def __init__(self, nodes: Optional[List[ClusterNode]] = None, max_concurrent_jobs: int = 8):
        self.nodes = nodes or [ClusterNode(0, "localhost", list(range(torch.cuda.device_count() if _cuda_available() else 1)))]
        self.node_gpu_availability: Dict[int, List[int]] = {n.node_id: list(n.gpu_ids) for n in self.nodes}
        self.max_concurrent_jobs = max_concurrent_jobs
        self.jobs: Dict[str, ClusterJob] = {}
        self.running_jobs: Dict[str, ClusterJob] = {}
        self.job_counter = 0

    def submit_job(self, num_gpus: int, fn: Callable, priority: int = 0, required_memory: int = 0, args: Tuple = (), kwargs: Optional[Dict[str, Any]] = None) -> str:
        job_id = f"job_{self.job_counter:06d}"
        self.job_counter += 1
        job = ClusterJob(job_id=job_id, num_gpus=num_gpus, priority=priority, required_memory=required_memory, fn=fn, args=args, kwargs=kwargs or {})
        self.jobs[job_id] = job
        self._try_schedule(job)
        return job_id

    def _try_schedule(self, job: ClusterJob) -> bool:
        if job.status != JobStatus.PENDING:
            return False
        for node in self.nodes:
            if len(self.node_gpu_availability.get(node.node_id, [])) >= job.num_gpus:
                assigned = self.node_gpu_availability[node.node_id][: job.num_gpus]
                self.node_gpu_availability[node.node_id] = self.node_gpu_availability[node.node_id][job.num_gpus :]
                job.assigned_node = node.node_id
                job.assigned_gpus = assigned
                job.status = JobStatus.RUNNING
                job.started_at = datetime.utcnow().isoformat()
                self.running_jobs[job.job_id] = job
                logger.info("Scheduled job %s on node %d, GPUs %s", job.job_id, node.node_id, assigned)
                return True
        return False

    def complete_job(self, job_id: str, result: Any = None) -> None:
        if job_id not in self.running_jobs:
            return
        job = self.running_jobs.pop(job_id)
        job.status = JobStatus.COMPLETED
        job.result = result
        job.completed_at = datetime.utcnow().isoformat()
        if job.assigned_node is not None:
            self.node_gpu_availability[job.assigned_node].extend(job.assigned_gpus)
        self._schedule_pending()

    def fail_job(self, job_id: str, error: str = "") -> None:
        if job_id not in self.running_jobs:
            return
        job = self.running_jobs.pop(job_id)
        job.status = JobStatus.FAILED
        job.error = error
        job.completed_at = datetime.utcnow().isoformat()
        if job.assigned_node is not None:
            self.node_gpu_availability[job.assigned_node].extend(job.assigned_gpus)
        self._schedule_pending()

    def cancel_job(self, job_id: str) -> bool:
        if job_id in self.running_jobs:
            job = self.running_jobs.pop(job_id)
            job.status = JobStatus.CANCELLED
            if job.assigned_node is not None:
                self.node_gpu_availability[job.assigned_node].extend(job.assigned_gpus)
            return True
        if job_id in self.jobs:
            self.jobs[job_id].status = JobStatus.CANCELLED
            return True
        return False

    def _schedule_pending(self) -> None:
        for job in sorted(self.jobs.values(), key=lambda j: -j.priority):
            if job.status == JobStatus.PENDING:
                self._try_schedule(job)

    def get_job_status(self, job_id: str) -> Optional[str]:
        if job_id in self.running_jobs:
            return self.running_jobs[job_id].status.value
        return self.jobs.get(job_id).status.value if job_id in self.jobs else None

    def get_cluster_status(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "gpu_availability": {n.node_id: len(self.node_gpu_availability[n.node_id]) for n in self.nodes},
            "running_jobs": len(self.running_jobs),
            "pending_jobs": sum(1 for j in self.jobs.values() if j.status == JobStatus.PENDING),
        }

    def wait_for_job(self, job_id: str, poll_interval: float = 1.0) -> Optional[Any]:
        while True:
            if job_id not in self.running_jobs:
                job = self.jobs.get(job_id)
                if job and job.status == JobStatus.COMPLETED:
                    return job.result
                return None
            time.sleep(poll_interval)

    def get_available_gpus(self) -> Dict[int, int]:
        return {node_id: len(gpus) for node_id, gpus in self.node_gpu_availability.items()}


def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False
