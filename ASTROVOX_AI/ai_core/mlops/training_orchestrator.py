from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class TrainingJob:
    job_id: str
    model_type: str
    hyperparameters: Dict[str, Any]
    status: str = "pending"
    metrics: Dict[str, float] = field(default_factory=dict)


class TrainingOrchestrator:
    def __init__(self):
        self.jobs: Dict[str, TrainingJob] = {}

    def submit(self, model_type: str, hyperparameters: Dict[str, Any]) -> TrainingJob:
        job = TrainingJob(job_id=str(len(self.jobs) + 1), model_type=model_type, hyperparameters=hyperparameters)
        self.jobs[job.job_id] = job
        return job

    def get_status(self, job_id: str) -> TrainingJob:
        return self.jobs.get(job_id)
