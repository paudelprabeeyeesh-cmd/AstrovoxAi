import logging
import uuid
import base64
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..auth import require_verified_email
from repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["images"])


@router.post("/images/generate")
async def generate_image(prompt: str, size: str = "1024x1024", user_id: str = Depends(require_verified_email)):
    try:
        image_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO images (id, user_id, prompt, size, created_at) VALUES (?, ?, ?, ?, ?)",
                (image_id, user_id, prompt[:1000], size, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": image_id, "prompt": prompt[:200], "size": size, "url": f"/images/{image_id}"}
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/images/understand")
async def understand_image(file: UploadFile = File(...), question: str = "", user_id: str = Depends(require_verified_email)):
    try:
        content = await file.read()
        analysis_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO image_analyses (id, user_id, filename, question, result, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (analysis_id, user_id, file.filename, question[:500], "[analysis placeholder]", datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": analysis_id, "filename": file.filename, "question": question, "result": "[analysis placeholder]"}
    except Exception as e:
        logger.error(f"Image understanding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/{image_id}")
async def get_image(image_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, user_id, prompt, size, created_at FROM images WHERE id = ? AND user_id = ?",
            (image_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Image not found")
        return dict(row)
