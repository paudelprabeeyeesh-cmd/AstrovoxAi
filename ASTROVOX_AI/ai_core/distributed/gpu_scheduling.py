from typing import Dict, Any, List, Optional, Tuple
import torch
import torch.cuda as cuda
from collections import deque


class GPUScheduler:
    def __init__(self, num_gpus: int = 1, memory_fraction: float = 0.9):
        self.num_gpus = num_gpus
        self.memory_fraction = memory_fraction
        self.gpu_queues: Dict[int, deque] = {i: deque() for i in range(num_gpus)}
        self.running_jobs: Dict[int, Dict[str, Any]] = {}
        self.job_id_counter = 0

    def submit_job(self, gpu_id: int, job_fn: callable, args: tuple = (), kwargs: Optional[Dict] = None, priority: int = 0) -> int:
        job_id = self.job_id_counter
        self.job_id_counter += 1
        self.gpu_queues[gpu_id].append({'id': job_id, 'fn': job_fn, 'args': args, 'kwargs': kwargs or {}, 'priority': priority})
        return job_id

    def schedule_next(self, gpu_id: int) -> Optional[Dict[str, Any]]:
        if not self.gpu_queues[gpu_id]:
            return None
        available_memory = self.get_available_memory(gpu_id)
        if available_memory < 100 * 1024 * 1024:
            return None
        job = self.gpu_queues[gpu_id].popleft()
        self.running_jobs[job['id']] = {'gpu_id': gpu_id, 'job': job}
        return job

    def get_available_memory(self, gpu_id: int) -> int:
        if gpu_id < cuda.device_count():
            total = cuda.get_device_properties(gpu_id).total_memory
            allocated = cuda.memory_allocated(gpu_id)
            return int((total - allocated) * self.memory_fraction)
        return 0

    def finish_job(self, job_id: int) -> None:
        if job_id in self.running_jobs:
            del self.running_jobs[job_id]
