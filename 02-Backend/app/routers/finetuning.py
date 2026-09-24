import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from ..database import get_db
from ..schemas import FineTuningDeployRequest, FineTuningJobCreate, FineTuningJobStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finetuning"])


@router.post("/finetuning/jobs", response_model=FineTuningJobStatus)
async def create_finetuning_job(req: FineTuningJobCreate, user_id: str = Depends(require_verified_email)):
    try:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                "INSERT INTO finetuning_jobs (id, user_id, model, training_file, validation_file, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (job_id, user_id, req.model, req.training_file, req.validation_file, "queued", now),
            )
            conn.commit()
        return FineTuningJobStatus(id=job_id, status="queued", model=req.model, fine_tuned_model=None, created_at=datetime.now(timezone.utc), finished_at=None, trained_tokens=None)
    except Exception as _e:  # noqa: BLE001
        logger.error(f"Finetuning job creation failed: {_e}")
        raise HTTPException(status_code=500, detail=str(_e)) from None


@router.get("/finetuning/jobs")
async def list_finetuning_jobs(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, model, status, training_file, created_at, completed_at FROM finetuning_jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/finetuning/jobs/{job_id}", response_model=FineTuningJobStatus)
async def get_finetuning_job(job_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, model, training_file, validation_file, status, created_at, completed_at, trained_tokens, fine_tuned_model FROM finetuning_jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        return FineTuningJobStatus(
            id=row["id"],
            status=row["status"],
            model=row["model"],
            fine_tuned_model=row.get("fine_tuned_model"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(timezone.utc),
            finished_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            trained_tokens=row.get("trained_tokens"),
        )


@router.post("/finetuning/jobs/{job_id}/deploy")
async def deploy_finetuned_model(job_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, status, fine_tuned_model FROM finetuning_jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        if row["status"] != "completed":
            raise HTTPException(status_code=400, detail="Job not completed")
        model_name = row.get("fine_tuned_model") or f"ft-{user_id[:8]}-{job_id[:8]}"
        return {"model": model_name, "status": "deployed"}


@router.post("/finetuning/export")
async def export_finetuning_data(req: dict, user_id: str = Depends(require_verified_email)):
    limit = req.get("limit", 5000)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT prompt, response FROM interactions WHERE user_id = ? LIMIT ?",
            (user_id, limit),
        ).fetchall()
        data = [{"prompt": r["prompt"], "response": r["response"]} for r in rows]
    return {"count": len(data), "data": data}
