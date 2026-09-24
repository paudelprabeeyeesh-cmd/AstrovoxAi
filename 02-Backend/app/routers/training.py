import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from ..auth import require_admin, require_verified_email
from ..database import get_db
from ..schemas import TrainingDatasetCreate, TrainingDatasetOut, TrainingJobCreate, TrainingJobOut

logger = logging.getLogger(__name__)

router = APIRouter(tags=["training"])

STORAGE_ROOT = Path(os.getenv("STORAGE_ROOT", "./storage"))
ALLOWED_TRAINING_CONTENT_TYPES = {
    "application/json",
    "application/jsonl",
    "text/plain",
    "application/octet-stream",
}
MAX_TRAINING_UPLOAD_SIZE = 50 * 1024 * 1024


def _ensure_storage_dir() -> None:
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def _save_upload(user_id: str, filename: str, content: bytes) -> str:
    _ensure_storage_dir()
    safe_name = f"{uuid.uuid4().hex}_{filename}"
    target = STORAGE_ROOT / "training" / user_id / safe_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return str(target)


@router.post("/training/upload", response_model=TrainingDatasetOut)
async def upload_training_dataset(
    name: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(require_admin),
):
    if file.content_type not in ALLOWED_TRAINING_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported content type")
    content = await file.read()
    if len(content) > MAX_TRAINING_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    path = _save_upload(user_id, file.filename or "dataset.jsonl", content)
    dataset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO training_datasets (id, user_id, name, filename, content_type, size, path, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (dataset_id, user_id, name, file.filename or "dataset.jsonl", file.content_type or "application/octet-stream", len(content), path, "uploaded", now),
        )
        conn.commit()
    return TrainingDatasetOut(
        id=dataset_id,
        user_id=user_id,
        name=name,
        filename=file.filename or "dataset.jsonl",
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        path=path,
        status="uploaded",
        created_at=datetime.now(timezone.utc),
    )


@router.get("/training/datasets", response_model=list[TrainingDatasetOut])
async def list_training_datasets(user_id: str = Depends(require_admin)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, user_id, name, filename, content_type, size, path, status, created_at FROM training_datasets ORDER BY created_at DESC LIMIT 100",
        ).fetchall()
        result = []
        for r in rows:
            result.append(TrainingDatasetOut(
                id=r["id"],
                user_id=r["user_id"],
                name=r["name"],
                filename=r["filename"],
                content_type=r["content_type"],
                size=r["size"],
                path=r["path"],
                status=r["status"],
                created_at=datetime.fromisoformat(r["created_at"]) if r.get("created_at") else datetime.now(timezone.utc),
            ))
        return result


@router.post("/training/jobs", response_model=TrainingJobOut)
async def create_training_job(req: TrainingJobCreate, user_id: str = Depends(require_verified_email)):
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO finetuning_jobs (id, user_id, model, training_file, validation_file, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, user_id, req.model, req.training_file, req.validation_file, "queued", now),
        )
        conn.commit()
    return TrainingJobOut(
        id=job_id,
        user_id=user_id,
        model=req.model,
        training_file=req.training_file,
        validation_file=req.validation_file,
        status="queued",
        fine_tuned_model=None,
        created_at=datetime.now(timezone.utc),
        completed_at=None,
        trained_tokens=None,
    )


@router.get("/training/jobs/{job_id}", response_model=TrainingJobOut)
async def get_training_job(job_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, model, training_file, validation_file, status, created_at, completed_at, trained_tokens, fine_tuned_model FROM finetuning_jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        return TrainingJobOut(
            id=row["id"],
            user_id=row["user_id"],
            model=row["model"],
            training_file=row["training_file"],
            validation_file=row.get("validation_file"),
            status=row["status"],
            fine_tuned_model=row.get("fine_tuned_model"),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(timezone.utc),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            trained_tokens=row.get("trained_tokens"),
        )


@router.post("/training/jobs/{job_id}/start")
async def start_training(job_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, status FROM finetuning_jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        if row["status"] not in ("queued", "failed"):
            raise HTTPException(status_code=400, detail=f"Cannot start job in status: {row['status']}")
        conn.execute(
            "UPDATE finetuning_jobs SET status = 'training' WHERE id = ?",
            (job_id,),
        )
        conn.commit()
    return {"id": job_id, "status": "training"}


@router.post("/training/jobs/{job_id}/complete")
async def complete_training(job_id: str, user_id: str = Depends(require_verified_email)):
    fine_tuned_model = f"ft-{user_id[:8]}-{job_id[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, status FROM finetuning_jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        conn.execute(
            "UPDATE finetuning_jobs SET status = 'completed', completed_at = ?, fine_tuned_model = ?, trained_tokens = COALESCE(trained_tokens, ?) WHERE id = ?",
            (now, fine_tuned_model, 1000, job_id),
        )
        conn.commit()
    return {"id": job_id, "status": "completed", "fine_tuned_model": fine_tuned_model}
