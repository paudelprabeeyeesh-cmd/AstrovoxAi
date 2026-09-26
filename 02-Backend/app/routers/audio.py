import logging
import uuid
import os
from datetime import datetime, timezone
from typing import Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from ..auth import require_verified_email
from app.repositories.database.client import get_db
from app.audio.voice_cloning import VoiceCloner
from app.audio.noise_removal import NoiseRemover
from app.audio.speaker_identification import SpeakerIdentifier
from app.audio.music_generation import MusicGenerator
from app.audio.podcast_summarization import PodcastSummarizer
from app.audio.emotion_detection import EmotionDetector
from app.audio.speech_to_text import SpeechToText
from app.audio.text_to_speech import TextToSpeech

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audio-ai"])

voice_cloner = VoiceCloner()
noise_remover = NoiseRemover()
speaker_identifier = SpeakerIdentifier()
music_generator = MusicGenerator()
podcast_summarizer = PodcastSummarizer()
emotion_detector = EmotionDetector()
speech_to_text = SpeechToText()
text_to_speech = TextToSpeech()


class TTSRequest(BaseModel):
    text: str = Field(..., max_length=5000)
    voice: str = "default"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class VoiceCloneRequest(BaseModel):
    voice_name: str = Field(..., max_length=100)
    text: str = Field(..., max_length=500)


class MusicGenRequest(BaseModel):
    prompt: str = Field(..., max_length=1000)
    duration: int = Field(default=30, ge=5, le=300)


class EmotionRequest(BaseModel):
    segment_duration: float = Field(default=5.0, ge=1.0, le=30.0)


class PodcastSummaryRequest(BaseModel):
    max_summary_length: int = Field(default=500, ge=100, le=2000)
    include_transcript: bool = True


class SpeakerEnrollRequest(BaseModel):
    speaker_id: str = Field(..., max_length=100)
    metadata: Optional[dict] = None


@router.post("/audio/tts")
async def text_to_speech(request: TTSRequest, user_id: str = Depends(require_verified_email)):
    try:
        result = text_to_speech.synthesize(request.text, voice=request.voice, speed=request.speed)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO audio_outputs (id, user_id, type, text, voice, output_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, "tts", request.text[:1000], request.voice, result.get("output_path", ""), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return result
    except Exception as exc:
        logger.error(f"TTS failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/audio/stt")
async def speech_to_text(file: UploadFile = File(...), language: Optional[str] = Form(None), user_id: str = Depends(require_verified_email)):
    try:
        suffix = Path(file.filename).suffix if file.filename else ".wav"
        tmp_path = f"/tmp/astrovox_stt_{uuid.uuid4().hex}{suffix}"
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
        result = speech_to_text.transcribe(tmp_path, language=language)
        result["filename"] = file.filename
        with get_db() as conn:
            conn.execute(
                "INSERT INTO audio_outputs (id, user_id, type, text, output_path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, "stt", result.get("text", "")[:1000], tmp_path, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return result
    except Exception as exc:
        logger.error(f"STT failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/audio/clone")
async def clone_voice(request: VoiceCloneRequest, user_id: str = Depends(require_verified_email)):
    try:
        if not request.text:
            raise HTTPException(status_code=400, detail="Text is required for voice cloning")
        existing = voice_cloner.list_voices(user_id=user_id)
        if not existing:
            raise HTTPException(status_code=400, detail="No voice profile found. Please upload reference audio first.")
        voice_id = existing[0]["voice_id"]
        result = voice_cloner.clone_voice(voice_id, request.text)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO audio_outputs (id, user_id, type, text, voice, output_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, "voice_clone", request.text[:1000], voice_id, result.get("output_path", ""), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Voice cloning failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/audio/voices/enroll")
async def enroll_voice(files: List[UploadFile] = File(...), voice_name: str = Form(...), user_id: str = Depends(require_verified_email)):
    try:
        tmp_paths = []
        for upload in files:
            suffix = Path(upload.filename).suffix if upload.filename else ".wav"
            tmp_path = f"/tmp/astrovox_enroll_{uuid.uuid4().hex}{suffix}"
            content = await upload.read()
            with open(tmp_path, "wb") as f:
                f.write(content)
            tmp_paths.append(tmp_path)
        profile = voice_cloner.register_voice(user_id, tmp_paths, voice_name)
        return profile
    except Exception as exc:
        logger.error(f"Voice enrollment failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        for path in tmp_paths:
            if os.path.exists(path):
                os.remove(path)


@router.get("/audio/voices")
async def list_voices(user_id: str = Depends(require_verified_email)):
    return voice_cloner.list_voices(user_id=user_id)


@router.delete("/audio/voices/{voice_id}")
async def delete_voice(voice_id: str, user_id: str = Depends(require_verified_email)):
    success = voice_cloner.delete_voice(voice_id)
    if not success:
        raise HTTPException(status_code=404, detail="Voice not found")
    return {"status": "deleted", "voice_id": voice_id}


@router.post("/audio/noise-removal")
async def remove_noise(file: UploadFile = File(...), strength: float = Form(0.5), user_id: str = Depends(require_verified_email)):
    try:
        suffix = Path(file.filename).suffix if file.filename else ".wav"
        tmp_path = f"/tmp/astrovox_noise_{uuid.uuid4().hex}{suffix}"
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
        result = noise_remover.remove_noise(tmp_path, strength=strength)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO audio_outputs (id, user_id, type, text, output_path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, "noise_removal", "", result.get("output_path", ""), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return result
    except Exception as exc:
        logger.error(f"Noise removal failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/audio/speakers/enroll")
async def enroll_speaker(request: SpeakerEnrollRequest, files: List[UploadFile] = File(...), user_id: str = Depends(require_verified_email)):
    try:
        tmp_paths = []
        for upload in files:
            suffix = Path(upload.filename).suffix if upload.filename else ".wav"
            tmp_path = f"/tmp/astrovox_speaker_{uuid.uuid4().hex}{suffix}"
            content = await upload.read()
            with open(tmp_path, "wb") as f:
                f.write(content)
            tmp_paths.append(tmp_path)
        profile = speaker_identifier.enroll_speaker(request.speaker_id, tmp_paths, request.metadata)
        return profile
    except Exception as exc:
        logger.error(f"Speaker enrollment failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        for path in tmp_paths:
            if os.path.exists(path):
                os.remove(path)


@router.post("/audio/speakers/identify")
async def identify_speaker(file: UploadFile = File(...), threshold: float = Form(0.7), user_id: str = Depends(require_verified_email)):
    try:
        suffix = Path(file.filename).suffix if file.filename else ".wav"
        tmp_path = f"/tmp/astrovox_identify_{uuid.uuid4().hex}{suffix}"
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
        result = speaker_identifier.identify_speaker(tmp_path, threshold=threshold)
        return result
    except Exception as exc:
        logger.error(f"Speaker identification failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/audio/speakers/diarize")
async def diarize_audio(file: UploadFile = File(...), num_speakers: Optional[int] = Form(None), user_id: str = Depends(require_verified_email)):
    try:
        suffix = Path(file.filename).suffix if file.filename else ".wav"
        tmp_path = f"/tmp/astrovox_diarize_{uuid.uuid4().hex}{suffix}"
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
        result = speaker_identifier.diarize_audio(tmp_path, num_speakers=num_speakers)
        return result
    except Exception as exc:
        logger.error(f"Diarization failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/audio/speakers")
async def list_speakers(user_id: str = Depends(require_verified_email)):
    return speaker_identifier.list_speakers()


@router.delete("/audio/speakers/{speaker_id}")
async def delete_speaker(speaker_id: str, user_id: str = Depends(require_verified_email)):
    success = speaker_identifier.delete_speaker(speaker_id)
    if not success:
        raise HTTPException(status_code=404, detail="Speaker not found")
    return {"status": "deleted", "speaker_id": speaker_id}


@router.post("/audio/music/generate")
async def generate_music(request: MusicGenRequest, user_id: str = Depends(require_verified_email)):
    try:
        result = music_generator.generate(request.prompt, duration=request.duration)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO audio_outputs (id, user_id, type, text, output_path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, "music_generation", request.prompt[:1000], result.get("output_path", ""), datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return result
    except Exception as exc:
        logger.error(f"Music generation failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/audio/podcast/summarize")
async def summarize_podcast(file: UploadFile = File(...), max_summary_length: int = Form(500), include_transcript: bool = Form(True), user_id: str = Depends(require_verified_email)):
    try:
        suffix = Path(file.filename).suffix if file.filename else ".wav"
        tmp_path = f"/tmp/astrovox_podcast_{uuid.uuid4().hex}{suffix}"
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
        result = podcast_summarizer.summarize(tmp_path, max_summary_length=max_summary_length, include_transcript=include_transcript)
        return result
    except Exception as exc:
        logger.error(f"Podcast summarization failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/audio/emotion/detect")
async def detect_emotion(file: UploadFile = File(...), segment_duration: float = Form(5.0), user_id: str = Depends(require_verified_email)):
    try:
        suffix = Path(file.filename).suffix if file.filename else ".wav"
        tmp_path = f"/tmp/astrovox_emotion_{uuid.uuid4().hex}{suffix}"
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)
        result = emotion_detector.detect(tmp_path, segment_duration=segment_duration)
        return result
    except Exception as exc:
        logger.error(f"Emotion detection failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
