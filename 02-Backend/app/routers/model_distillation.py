import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email, require_admin
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["distillation"])


@router.post("/distillation/jobs")
async def create_distillation_job(req: dict, user_id: str = Depends(require_admin)):
    job_id = str(uuid.uuid4())
    teacher_model = req.get("teacher_model", "gpt-4o")
    student_model = req.get("student_model", "gpt-4o-mini")
    dataset_path = req.get("dataset_path", "")
    alpha = req.get("alpha", 0.7)
    beta = req.get("beta", 0.3)
    temperature = req.get("temperature", 1.0)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO distillation_jobs (id, user_id, teacher_model, student_model, dataset_path, alpha, beta, temperature, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, user_id, teacher_model, student_model, dataset_path, alpha, beta, temperature, "queued", datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {
        "job_id": job_id,
        "teacher_model": teacher_model,
        "student_model": student_model,
        "alpha": alpha,
        "beta": beta,
        "temperature": temperature,
        "status": "queued",
    }


@router.get("/distillation/jobs")
async def list_distillation_jobs(user_id: str = Depends(require_admin)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, teacher_model, student_model, status, alpha, beta, created_at, completed_at FROM distillation_jobs ORDER BY created_at DESC LIMIT 50",
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/distillation/jobs/{job_id}")
async def get_distillation_job(job_id: str, user_id: str = Depends(require_admin)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, teacher_model, student_model, dataset_path, alpha, beta, temperature, status, created_at, completed_at FROM distillation_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        return dict(row)


@router.post("/distillation/jobs/{job_id}/quantize")
async def quantize_model(job_id: str, req: dict, user_id: str = Depends(require_admin)):
    bits = req.get("bits", 8)
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, student_model, status FROM distillation_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        quantized_model = f"{row['student_model']}-int{bits}"
        conn.execute(
            "INSERT INTO quantization_logs (id, job_id, model, bits, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), job_id, quantized_model, bits, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {
        "job_id": job_id,
        "quantized_model": quantized_model,
        "bits": bits,
        "original_size": "4.2GB",
        "quantized_size": f"{round(4.2 * (bits / 32), 2)}GB",
    }
