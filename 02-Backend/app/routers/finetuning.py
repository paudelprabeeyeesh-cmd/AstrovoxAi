import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["finetuning"])


@router.post("/finetuning/jobs")
async def create_finetuning_job(req: dict, user_id: str = Depends(require_verified_email)):
    try:
        job_id = str(uuid.uuid4())
        model = req.get("model", "gpt-4o-mini")
        training_file = req.get("training_file", "")
        validation_file = req.get("validation_file")
        with get_db() as conn:
            conn.execute(
                "INSERT INTO finetuning_jobs (id, user_id, model, training_file, validation_file, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (job_id, user_id, model, training_file, validation_file, "queued", datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": job_id, "model": model, "status": "queued"}
    except Exception as e:
        logger.error(f"Finetuning job creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/finetuning/jobs")
async def list_finetuning_jobs(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, model, status, training_file, created_at, completed_at FROM finetuning_jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/finetuning/jobs/{job_id}")
async def get_finetuning_job(job_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, model, training_file, validation_file, status, created_at, completed_at FROM finetuning_jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        return dict(row)


@router.post("/finetuning/jobs/{job_id}/deploy")
async def deploy_finetuned_model(job_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, status FROM finetuning_jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        if row["status"] != "completed":
            raise HTTPException(status_code=400, detail="Job not completed")
        model_name = f"ft-{user_id[:8]}-{job_id[:8]}"
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
