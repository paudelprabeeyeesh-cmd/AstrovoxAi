import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..auth import require_verified_email
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])


@router.post("/voice/speak")
async def voice_speak_endpoint(text: str, voice: str = "default", user_id: str = Depends(require_verified_email)):
    try:
        speech_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO voice_outputs (id, user_id, text, voice, created_at) VALUES (?, ?, ?, ?, ?)",
                (speech_id, user_id, text[:1000], voice, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": speech_id, "text": text[:200], "voice": voice, "status": "generated"}
    except Exception as e:
        logger.error(f"Voice synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/transcribe")
async def voice_transcribe_endpoint(file: UploadFile = File(...), user_id: str = Depends(require_verified_email)):
    try:
        content = await file.read()
        transcript_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO voice_transcripts (id, user_id, filename, content, transcript, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (transcript_id, user_id, file.filename, content, "[transcript placeholder]", datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": transcript_id, "filename": file.filename, "transcript": "[transcript placeholder]"}
    except Exception as e:
        logger.error(f"Voice transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
