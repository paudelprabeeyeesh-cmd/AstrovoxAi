import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from ..auth import require_verified_email, require_admin
from repositories.database.client import get_db
from ...schemas import BatchJobCreate, BatchJobOut
from ..core.tracing import start_trace

logger = logging.getLogger(__name__)

router = APIRouter(tags=["batch"])


@router.post("/batch/jobs")
async def create_batch_job(req: BatchJobCreate, user_id: str = Depends(require_verified_email)):
    job_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO batch_jobs (id, user_id, status, input_data, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, user_id, "queued", json.dumps(req.inputs), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"job_id": job_id, "status": "queued"}


@router.get("/batch/jobs/{job_id}")
async def get_batch_job(job_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, status, input_data, output_data, error, created_at, completed_at FROM batch_jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        return dict(row)


@router.get("/batch/jobs")
async def list_batch_jobs(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, status, created_at, completed_at FROM batch_jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.delete("/batch/jobs/{job_id}")
async def cancel_batch_job(job_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE batch_jobs SET status = 'cancelled' WHERE id = ? AND user_id = ? AND status IN ('queued', 'running')",
            (job_id, user_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Job not found or already completed")
    return {"ok": True}
