import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audio-ai"])

OUTPUT_DIR = Path("/tmp/astrovox_audio")


@router.get("/audio/outputs/{filename}")
async def get_audio_output(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        for sub in ["/tmp/astrovox_tts", "/tmp/astrovox_music", "/tmp/astrovox_voices", "/tmp/astrovox_noise"]:
            candidate = Path(sub) / filename
            if candidate.exists():
                return FileResponse(candidate, media_type="audio/mpeg" if filename.endswith(".mp3") else "audio/wav")
        raise HTTPException(status_code=404, detail="Audio output not found")
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    return FileResponse(file_path, media_type=media_type)
