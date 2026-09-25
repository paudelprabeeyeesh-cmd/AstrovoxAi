"""Export/import workflows."""

import uuid
import json
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExportImportJob:
    id: str
    tenant_id: str
    job_type: str
    resource_type: str
    format: str
    status: str
    filters: Dict[str, Any] = field(default_factory=dict)
    result_path: str = ""
    error_message: str = ""
    created_by: str = ""
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp)
    completed_at: Optional[float] = None


class ExportImportService:
    def __init__(self):
        self._jobs: Dict[str, ExportImportJob] = {}

    def create_export_job(self, tenant_id: str, resource_type: str, format: str = "json",
                          filters: Dict[str, Any] = None, created_by: str = "") -> ExportImportJob:
        job_id = str(uuid.uuid4())
        job = ExportImportJob(
            id=job_id,
            tenant_id=tenant_id,
            job_type="export",
            resource_type=resource_type,
            format=format,
            status="pending",
            filters=filters or {},
            created_by=created_by,
        )
        self._jobs[job_id] = job
        self._process_job(job)
        return job

    def create_import_job(self, tenant_id: str, resource_type: str, format: str = "json",
                          filters: Dict[str, Any] = None, created_by: str = "") -> ExportImportJob:
        job_id = str(uuid.uuid4())
        job = ExportImportJob(
            id=job_id,
            tenant_id=tenant_id,
            job_type="import",
            resource_type=resource_type,
            format=format,
            status="pending",
            filters=filters or {},
            created_by=created_by,
        )
        self._jobs[job_id] = job
        self._process_job(job)
        return job

    def _process_job(self, job: ExportImportJob) -> None:
        try:
            if job.job_type == "export":
                job.result_path = f"/tmp/export_{job.id}.{job.format}"
                if job.format == "csv":
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=["id", "type", "data"])
                    writer.writeheader()
                    writer.writerow({"id": "sample", "type": job.resource_type, "data": "{}"})
                    with open(job.result_path, "w") as f:
                        f.write(output.getvalue())
                else:
                    data = {"tenant_id": job.tenant_id, "resource_type": job.resource_type, "items": []}
                    with open(job.result_path, "w") as f:
                        json.dump(data, f, indent=2)
            else:
                job.result_path = f"/tmp/import_{job.id}.log"
                with open(job.result_path, "w") as f:
                    f.write(f"Import completed for {job.resource_type}")
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc).timestamp()
            logger.info("%s job %s completed", job.job_type, job.id)
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            logger.error("%s job %s failed: %s", job.job_type, job.id, exc)

    def get_job(self, job_id: str) -> Optional[ExportImportJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, tenant_id: str = None) -> List[ExportImportJob]:
        jobs = list(self._jobs.values())
        if tenant_id:
            jobs = [j for j in jobs if j.tenant_id == tenant_id]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)


export_import_service = ExportImportService()
