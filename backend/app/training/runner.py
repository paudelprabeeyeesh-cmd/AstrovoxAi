import logging
import threading
from typing import Dict, Optional

from .service import TrainingService, training_jobs

logger = logging.getLogger(__name__)


class TrainingRunner:
    def __init__(self, service: TrainingService):
        self.service = service
        self._threads: Dict[str, threading.Thread] = {}

    def start_job(self, job_id: str, dataloader_factory):
        job = self.service.get_job(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")

        def run():
            try:
                job.setup()
                job.status = "running"
                for epoch in range(job.epochs):
                    dataloader = dataloader_factory()
                    job.run_epoch(dataloader)
                job.status = "completed"
            except Exception as exc:
                job.status = "failed"
                logger.exception("Training job %s failed: %s", job_id, exc)

        thread = threading.Thread(target=run, daemon=True)
        self._threads[job_id] = thread
        thread.start()
        return thread

    def stop_job(self, job_id: str):
        if job_id in self._threads:
            self._threads[job_id] = None
            logger.info("Stop requested for job %s", job_id)
