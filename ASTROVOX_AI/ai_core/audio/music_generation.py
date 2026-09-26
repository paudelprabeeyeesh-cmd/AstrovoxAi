import os
import uuid
import logging
import tempfile
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

from ..audio import AudioUtils

logger = logging.getLogger(__name__)


class MusicGenerator:
    def __init__(self, model_name: str = "musicgen-medium"):
        self.model_name = model_name
        self.generated_tracks: Dict[str, Dict[str, Any]] = {}
        self.temp_dir = Path(tempfile.gettempdir()) / "astrovox_music"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str, duration: int = 30, output_path: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        if output_path is None:
            output_path = str(self.temp_dir / f"track_{uuid.uuid4().hex[:8]}.wav")
        try:
            import scipy.io.wavfile as wavfile
            from transformers import AutoProcessor, MusicgenForConditionalGeneration
            import torch
            processor = AutoProcessor.from_pretrained(f"facebook/{model or self.model_name}")
            model_instance = MusicgenForConditionalGeneration.from_pretrained(f"facebook/{model or self.model_name}")
            model_instance.eval()
            inputs = processor(text=[prompt[:500]], padding=True, return_tensors="pt")
            with torch.no_grad():
                audio_values = model_instance.generate(**inputs, max_new_tokens=duration * 50)
            audio_np = audio_values[0, 0].cpu().numpy()
            audio_np = np.clip(audio_np, -1.0, 1.0)
            wavfile.write(output_path, rate=32000, data=(audio_np * 32767).astype(np.int16))
            track_id = str(uuid.uuid4())
            result = {
                "track_id": track_id,
                "prompt": prompt[:500],
                "duration": duration,
                "output_path": output_path,
                "model": model or self.model_name,
                "status": "generated",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.generated_tracks[track_id] = result
            return result
        except Exception as exc:
            logger.error(f"Music generation failed: {exc}")
            if os.path.exists(output_path):
                os.remove(output_path)
            raise RuntimeError(f"Music generation failed: {exc}") from exc

    def generate_with_audio_conditioning(self, prompt: str, conditioning_audio: str, duration: int = 30) -> Dict[str, Any]:
        output_path = str(self.temp_dir / f"track_cond_{uuid.uuid4().hex[:8]}.wav")
        try:
            import scipy.io.wavfile as wavfile
            from transformers import AutoProcessor, MusicgenForConditionalGeneration
            import torch
            import librosa
            processor = AutoProcessor.from_pretrained(f"facebook/{self.model_name}")
            model_instance = MusicgenForConditionalGeneration.from_pretrained(f"facebook/{self.model_name}")
            model_instance.eval()
            cond_data, cond_sr = AudioUtils.load_audio(conditioning_audio, sr=32000)
            inputs = processor(audio=cond_data, sampling_rate=32000, text=[prompt[:500]], padding=True, return_tensors="pt")
            with torch.no_grad():
                audio_values = model_instance.generate(**inputs, max_new_tokens=duration * 50)
            audio_np = audio_values[0, 0].cpu().numpy()
            audio_np = np.clip(audio_np, -1.0, 1.0)
            wavfile.write(output_path, rate=32000, data=(audio_np * 32767).astype(np.int16))
            track_id = str(uuid.uuid4())
            result = {
                "track_id": track_id,
                "prompt": prompt[:500],
                "conditioning_audio": conditioning_audio,
                "duration": duration,
                "output_path": output_path,
                "status": "generated",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.generated_tracks[track_id] = result
            return result
        except Exception as exc:
            logger.error(f"Conditioned music generation failed: {exc}")
            if os.path.exists(output_path):
                os.remove(output_path)
            raise RuntimeError(f"Conditioned music generation failed: {exc}") from exc

    def list_tracks(self) -> List[Dict[str, Any]]:
        return list(self.generated_tracks.values())

    def delete_track(self, track_id: str) -> bool:
        if track_id not in self.generated_tracks:
            return False
        track = self.generated_tracks.pop(track_id)
        output_path = Path(track.get("output_path", ""))
        if output_path.exists():
            output_path.unlink()
        return True
