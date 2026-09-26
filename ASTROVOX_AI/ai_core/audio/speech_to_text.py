import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


class SpeechToText:
    def __init__(self, model_size: str = "base", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            import whisper
            self.model = whisper.load_model(self.model_size, device=self.device)
        except Exception as exc:
            logger.warning(f"Whisper model load failed: {exc}")

    def transcribe(self, audio_path: str, language: Optional[str] = None, task: str = "transcribe") -> Dict[str, Any]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if self.model is None:
            return {"text": "", "segments": [], "language": language or "unknown", "status": "model_unavailable"}
        try:
            result = self.model.transcribe(audio_path, language=language, task=task)
            text = result.get("text", "").strip()
            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "id": seg.get("id"),
                    "start": round(seg.get("start", 0), 2),
                    "end": round(seg.get("end", 0), 2),
                    "text": seg.get("text", "").strip(),
                })
            return {
                "text": text,
                "segments": segments,
                "language": result.get("language", language or "unknown"),
                "status": "completed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.error(f"Transcription failed: {exc}")
            return {"text": "", "segments": [], "error": str(exc), "status": "failed"}

    def transcribe_batch(self, audio_paths: List[str], language: Optional[str] = None) -> List[Dict[str, Any]]:
        return [self.transcribe(path, language=language) for path in audio_paths]

    def detect_language(self, audio_path: str) -> Dict[str, Any]:
        if self.model is None:
            return {"language": "unknown", "status": "model_unavailable"}
        try:
            result = self.model.transcribe(audio_path, task="transcribe")
            lang = result.get("language", "unknown")
            return {"language": lang, "status": "completed"}
        except Exception as exc:
            logger.error(f"Language detection failed: {exc}")
            return {"language": "unknown", "error": str(exc), "status": "failed"}
