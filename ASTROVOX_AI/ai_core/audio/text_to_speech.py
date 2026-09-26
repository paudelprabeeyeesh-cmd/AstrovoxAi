import os
import uuid
import logging
import tempfile
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

from ..audio import AudioUtils

logger = logging.getLogger(__name__)


class TextToSpeech:
    def __init__(self, default_voice: str = "default", engine: str = "openai"):
        self.default_voice = default_voice
        self.engine = engine
        self.temp_dir = Path(tempfile.gettempdir()) / "astrovox_tts"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.generated: Dict[str, Dict[str, Any]] = {}
        self.available_voices = self._load_voices()

    def _load_voices(self) -> List[Dict[str, str]]:
        return [
            {"id": "default", "name": "Default", "engine": "openai", "gender": "neutral"},
            {"id": "nova", "name": "Nova", "engine": "openai", "gender": "female"},
            {"id": "echo", "name": "Echo", "engine": "openai", "gender": "male"},
            {"id": "fable", "name": "Fable", "engine": "openai", "gender": "male"},
            {"id": "onyx", "name": "Onyx", "engine": "openai", "gender": "male"},
            {"id": "shimmer", "name": "Shimmer", "engine": "openai", "gender": "female"},
            {"id": "alloy", "name": "Alloy", "engine": "openai", "gender": "neutral"},
        ]

    def synthesize(self, text: str, voice: Optional[str] = None, output_path: Optional[str] = None, speed: float = 1.0) -> Dict[str, Any]:
        if not text or not text.strip():
            raise ValueError("Text must not be empty")
        voice = voice or self.default_voice
        if output_path is None:
            output_path = str(self.temp_dir / f"tts_{uuid.uuid4().hex[:8]}.mp3")
        try:
            if self.engine == "openai":
                self._openai_synthesize(text, voice, output_path, speed)
            elif self.engine == "edge_tts":
                self._edge_synthesize(text, voice, output_path, speed)
            else:
                raise ValueError(f"Unsupported TTS engine: {self.engine}")
            tts_id = str(uuid.uuid4())
            result = {
                "tts_id": tts_id,
                "text": text[:500],
                "voice": voice,
                "speed": speed,
                "output_path": output_path,
                "status": "generated",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.generated[tts_id] = result
            return result
        except Exception as exc:
            logger.error(f"TTS synthesis failed: {exc}")
            if os.path.exists(output_path):
                os.remove(output_path)
            raise RuntimeError(f"TTS synthesis failed: {exc}") from exc

    def synthesize_streaming(self, text: str, voice: Optional[str] = None, speed: float = 1.0):
        try:
            import openai
            client = openai.OpenAI()
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice or self.default_voice,
                input=text[:4096],
                response_format="mp3",
                speed=speed,
            )
            return response.content
        except Exception as exc:
            logger.error(f"Streaming TTS failed: {exc}")
            raise RuntimeError(f"Streaming TTS failed: {exc}") from exc

    def list_voices(self) -> List[Dict[str, str]]:
        return self.available_voices

    def get_audio_duration(self, audio_path: str) -> Optional[float]:
        try:
            info = AudioUtils.load_audio(audio_path)
            data, sr = info
            return round(len(data) / sr, 2)
        except Exception:
            return None

    def _openai_synthesize(self, text: str, voice: str, output_path: str, speed: float) -> None:
        import openai
        client = openai.OpenAI()
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text[:4096],
            response_format="mp3",
            speed=speed,
        )
        with open(output_path, "wb") as f:
            f.write(response.content)

    def _edge_synthesize(self, text: str, voice: str, output_path: str, speed: float) -> None:
        import edge_tts
        import asyncio
        async def _run():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
        asyncio.run(_run())
