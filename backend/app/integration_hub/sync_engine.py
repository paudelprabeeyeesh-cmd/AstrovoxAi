"""Synchronization engine for integration data."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncJob:
    job_id: str
    source_connector_id: str
    target_connector_id: str
    schedule: str
    transform: Optional[str] = None
    status: SyncStatus = SyncStatus.PENDING
    last_run: Optional[datetime] = None


class SyncEngine:
    def __init__(self) -> None:
        self._jobs: Dict[str, SyncJob] = {}

    def create_job(self, job: SyncJob) -> SyncJob:
        job.job_id = job.job_id or uuid.uuid4().hex
        self._jobs[job.job_id] = job
        return job

    async def run_job(self, job_id: str) -> Dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Unknown sync job: {job_id}")
        job.status = SyncStatus.RUNNING
        job.last_run = datetime.now(timezone.utc)
        try:
            job.status = SyncStatus.COMPLETED
            return {"job_id": job_id, "status": "completed"}
        except Exception as exc:
            job.status = SyncStatus.FAILED
            raise exc


sync_engine = SyncEngine()
