import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class ExportImportJob:
    id: str
    tenant_id: str
    job_type: str
    resource_type: str
    filters: Dict[str, Any] = field(default_factory=dict)
    format: str = "json"
    status: str = "pending"
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_by: str = ""
    created_at: float = field(default_factory=datetime.now(timezone.utc).timestamp)
    completed_at: Optional[float] = None


class ExportImportService:
    def __init__(self):
        self.jobs: Dict[str, ExportImportJob] = {}

    def create_export_job(self, tenant_id: str, resource_type: str, format: str = "json", filters: Dict[str, Any] = None, created_by: str = "") -> ExportImportJob:
        job_id = str(uuid.uuid4())
        job = ExportImportJob(
            id=job_id,
            tenant_id=tenant_id,
            job_type="export",
            resource_type=resource_type,
            filters=filters or {},
            format=format,
            created_by=created_by,
        )
        self.jobs[job_id] = job
        self._persist(job)
        self._process_export(job)
        return job

    def create_import_job(self, tenant_id: str, resource_type: str, format: str = "json", filters: Dict[str, Any] = None, created_by: str = "") -> ExportImportJob:
        job_id = str(uuid.uuid4())
        job = ExportImportJob(
            id=job_id,
            tenant_id=tenant_id,
            job_type="import",
            resource_type=resource_type,
            filters=filters or {},
            format=format,
            created_by=created_by,
        )
        self.jobs[job_id] = job
        self._persist(job)
        self._process_import(job)
        return job

    def _persist(self, job: ExportImportJob) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO export_import_jobs (id, tenant_id, job_type, resource_type, filters, format, status, file_path, error_message, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    job.id,
                    job.tenant_id,
                    job.job_type,
                    job.resource_type,
                    json.dumps(job.filters),
                    job.format,
                    job.status,
                    job.file_path,
                    job.error_message,
                    job.created_by,
                    datetime.fromtimestamp(job.created_at, tz=timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def _process_export(self, job: ExportImportJob) -> None:
        try:
            with get_db() as conn:
                rows = conn.execute(f"SELECT * FROM {job.resource_type}").fetchall()
                data = [dict(r) for r in rows]
                file_path = f"/tmp/export_{job.id}.{job.format}"
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2)
                job.status = "completed"
                job.file_path = file_path
                job.completed_at = datetime.now(timezone.utc).timestamp()
                with get_db() as conn:
                    conn.execute(
                        "UPDATE export_import_jobs SET status = 'completed', file_path = ?, completed_at = ? WHERE id = ?",
                        (file_path, datetime.fromtimestamp(job.completed_at, tz=timezone.utc).isoformat(), job.id),
                    )
                    conn.commit()
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            with get_db() as conn:
                conn.execute(
                    "UPDATE export_import_jobs SET status = 'failed', error_message = ? WHERE id = ?",
                    (str(exc), job.id),
                )
                conn.commit()

    def _process_import(self, job: ExportImportJob) -> None:
        try:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc).timestamp()
            with get_db() as conn:
                conn.execute(
                    "UPDATE export_import_jobs SET status = 'completed', completed_at = ? WHERE id = ?",
                    (datetime.fromtimestamp(job.completed_at, tz=timezone.utc).isoformat(), job.id),
                )
                conn.commit()
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            with get_db() as conn:
                conn.execute(
                    "UPDATE export_import_jobs SET status = 'failed', error_message = ? WHERE id = ?",
                    (str(exc), job.id),
                )
                conn.commit()

    def get_job(self, job_id: str) -> Optional[ExportImportJob]:
        return self.jobs.get(job_id)

    def list_jobs(self, tenant_id: str = None) -> List[ExportImportJob]:
        jobs = list(self.jobs.values())
        if tenant_id:
            jobs = [j for j in jobs if j.tenant_id == tenant_id]
        return jobs


export_import_service = ExportImportService()
