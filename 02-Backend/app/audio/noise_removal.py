import os
import uuid
import logging
import tempfile
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class NoiseRemover:
    def __init__(self, method: str = "spectral_gating"):
        self.method = method
        self.processed_files: Dict[str, Dict[str, Any]] = {}

    def remove_noise(self, audio_path: str, output_path: Optional[str] = None, strength: float = 0.5) -> Dict[str, Any]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if output_path is None:
            output_path = str(Path(audio_path).with_suffix(f".clean_{uuid.uuid4().hex[:8]}.wav"))
        try:
            if self.method == "spectral_gating":
                self._spectral_gate(audio_path, output_path, strength)
            elif self.method == "demucs":
                self._demucs_remove(audio_path, output_path)
            else:
                raise ValueError(f"Unknown noise removal method: {self.method}")
            result = {
                "input_path": audio_path,
                "output_path": output_path,
                "method": self.method,
                "strength": strength,
                "status": "completed",
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            self.processed_files[output_path] = result
            return result
        except Exception as exc:
            logger.error(f"Noise removal failed: {exc}")
            if os.path.exists(output_path):
                os.remove(output_path)
            raise RuntimeError(f"Noise removal failed: {exc}") from exc

    def batch_remove_noise(self, audio_paths: List[str], output_dir: str, strength: float = 0.5) -> List[Dict[str, Any]]:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        results = []
        for path in audio_paths:
            stem = Path(path).stem
            output_path = os.path.join(output_dir, f"{stem}_clean.wav")
            try:
                result = self.remove_noise(path, output_path, strength)
                results.append(result)
            except Exception as exc:
                logger.error(f"Batch noise removal failed for {path}: {exc}")
                results.append({"input_path": path, "error": str(exc), "status": "failed"})
        return results

    def _spectral_gate(self, input_path: str, output_path: str, strength: float) -> None:
        import soundfile as sf
        import scipy.signal as signal
        data, sr = sf.read(input_path)
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        f, t, Sxx = signal.spectrogram(data, sr)
        noise_floor = np.mean(Sxx, axis=1, keepdims=True)
        threshold = noise_floor + strength * np.std(Sxx, axis=1, keepdims=True)
        mask = Sxx > threshold
        Sxx_clean = Sxx * mask
        _, x_clean = signal.istft(Sxx_clean, sr)
        x_clean = x_clean[: len(data)]
        sf.write(output_path, x_clean, sr)

    def _demucs_remove(self, input_path: str, output_path: str) -> None:
        try:
            from demucs import pretrained
            from demucs.separate import separate_audio
            model = pretrained.get_model("htdemucs")
            out = separate_audio(model, input_path, output_dir=tempfile.gettempdir(), split=True)
            if out and os.path.exists(out):
                os.replace(out, output_path)
            else:
                raise RuntimeError("Demucs separation returned no output")
        except Exception as exc:
            logger.warning(f"Demucs failed, falling back to spectral gating: {exc}")
            self._spectral_gate(input_path, output_path, strength=0.5)
