"""Video AI API routes."""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Header, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field

from app.utils.auth.auth_utils import get_user_id_from_token
from app.video_ai import video_ai

router = APIRouter(prefix="/video", tags=["video-ai"])


class TextToVideoRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    image_base64: Optional[str] = None
    duration_seconds: float = Field(4.0, ge=1.0, le=60.0)
    width: int = Field(1024, ge=256, le=2048)
    height: int = Field(576, ge=256, le=2048)
    fps: int = Field(24, ge=1, le=60)
    model: Optional[str] = None
    seed: Optional[int] = None


class VideoSummarizeRequest(BaseModel):
    prompt: str = Field("Summarize the key events and content in this video.", min_length=1, max_length=2000)
    max_scenes: int = Field(5, ge=1, le=50)


class SceneDetectRequest(BaseModel):
    threshold: float = Field(0.3, ge=0.0, le=1.0)
    method: str = Field("histogram", min_length=1)


class SubtitleRequest(BaseModel):
    language: Optional[str] = None
    format: str = Field("srt", min_length=1)


class LipSyncRequest(BaseModel):
    fps: int = Field(25, ge=1, le=60)


class MotionTrackRequest(BaseModel):
    init_bbox: Optional[Dict[str, int]] = None


class InterpolateRequest(BaseModel):
    multiplier: int = Field(2, ge=2, le=16)
    method: str = Field("flow", min_length=1)


@router.post("/text-to-video")
async def text_to_video(request: TextToVideoRequest, authorization: str = Header(None)):
    try:
        user_id = get_user_id_from_token(authorization)
        result = video_ai.text_to_video(
            prompt=request.prompt,
            image_base64=request.image_base64,
            duration_seconds=request.duration_seconds,
            width=request.width,
            height=request.height,
            fps=request.fps,
            model=request.model,
            seed=request.seed,
        )
        result["user_id"] = user_id
        return {"status": "OK", **result}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/summarize")
async def summarize_video(file: UploadFile = File(...), prompt: str = "Summarize the key events and content in this video.", max_scenes: int = 5):
    try:
        content = await file.read()
        result = video_ai.summarize(content, prompt=prompt, max_scenes=max_scenes)
        return {"status": "OK", **result}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/scene-detect")
async def scene_detect(file: UploadFile = File(...), threshold: float = 0.3, method: str = "histogram"):
    try:
        content = await file.read()
        result = video_ai.detect_scenes(content, threshold=threshold, method=method)
        return {"status": "OK", **result}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/subtitles")
async def generate_subtitles(file: UploadFile = File(...), language: Optional[str] = None, format: str = "srt"):
    try:
        content = await file.read()
        result = video_ai.generate_subtitles(content, language=language, format=format)
        return {"status": "OK", **result}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/lip-sync")
async def lip_sync(video: UploadFile = File(...), audio: UploadFile = File(...), fps: int = 25):
    try:
        video_bytes = await video.read()
        audio_bytes = await audio.read()
        result = video_ai.lip_sync(video_bytes, audio_bytes, fps=fps)
        return {"status": "OK", **result}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/motion-track")
async def motion_track(file: UploadFile = File(...), init_bbox: Optional[Dict[str, int]] = None):
    try:
        content = await file.read()
        result = video_ai.track_motion(content, init_bbox=init_bbox)
        return {"status": "OK", **result}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/interpolate")
async def interpolate_frames(file: UploadFile = File(...), multiplier: int = 2, method: str = "flow"):
    try:
        content = await file.read()
        result = video_ai.interpolate(content, multiplier=multiplier, method=method)
        return {"status": "OK", **result}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/health")
async def video_health():
    return {
        "status": "ok",
        "features": [
            "text-to-video",
            "summarization",
            "scene-detection",
            "subtitle-generation",
            "lip-sync",
            "motion-tracking",
            "frame-interpolation",
        ],
    }
