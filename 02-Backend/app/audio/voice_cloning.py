import os
import uuid
import logging
import tempfile
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class VoiceCloner:
    def __init__(self, storage_dir: str = "/tmp/astrovox_voices"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.reference_samples: Dict[str, List[str]] = {}
        self.voice_profiles: Dict[str, Dict[str, Any]] = {}

    def register_voice(self, user_id: str, audio_paths: List[str], voice_name: str) -> Dict[str, Any]:
        voice_id = str(uuid.uuid4())
        profile_path = self.storage_dir / f"{voice_id}.npz"
        features = []
        valid_paths = []
        for path in audio_paths:
            if os.path.exists(path):
                try:
                    import soundfile as sf
                    data, sr = sf.read(path)
                    features.append(self._extract_features(data, sr))
                    valid_paths.append(path)
                except Exception as exc:
                    logger.warning(f"Skipping invalid audio sample {path}: {exc}")
        if not features:
            raise ValueError("No valid audio samples provided for voice cloning")
        mean_feature = np.mean(features, axis=0)
        np.savez(profile_path, mean_feature=mean_feature, samples=valid_paths)
        profile = {
            "voice_id": voice_id,
            "user_id": user_id,
            "name": voice_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sample_count": len(valid_paths),
            "profile_path": str(profile_path),
        }
        self.voice_profiles[voice_id] = profile
        if user_id not in self.reference_samples:
            self.reference_samples[user_id] = []
        self.reference_samples[user_id].extend(valid_paths)
        logger.info(f"Registered voice {voice_id} for user {user_id}")
        return profile

    def clone_voice(self, voice_id: str, text: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        if voice_id not in self.voice_profiles:
            raise ValueError(f"Voice profile {voice_id} not found")
        profile = self.voice_profiles[voice_id]
        if output_path is None:
            output_path = str(self.storage_dir / f"clone_{voice_id}_{uuid.uuid4().hex[:8]}.wav")
        try:
            import torch
            from TTS.api import TTS
            device = "cuda" if torch.cuda.is_available() else "cpu"
            tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False).to(device)
            reference = profile.get("profile_path")
            if reference and os.path.exists(reference):
                tts.tts_to_file(
                    text=text[:500],
                    file_path=output_path,
                    speaker_wav=profile["profile_path"],
                    language="en",
                )
            else:
                tts.tts_to_file(text=text[:500], file_path=output_path, language="en")
            return {
                "voice_id": voice_id,
                "text": text[:200],
                "output_path": output_path,
                "status": "generated",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.error(f"Voice cloning failed: {exc}")
            if os.path.exists(output_path):
                os.remove(output_path)
            raise RuntimeError(f"Voice cloning failed: {exc}") from exc

    def list_voices(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if user_id:
            return [p for p in self.voice_profiles.values() if p.get("user_id") == user_id]
        return list(self.voice_profiles.values())

    def delete_voice(self, voice_id: str) -> bool:
        if voice_id not in self.voice_profiles:
            return False
        profile = self.voice_profiles.pop(voice_id)
        profile_path = Path(profile.get("profile_path", ""))
        if profile_path.exists():
            profile_path.unlink()
        return True

    def _extract_features(self, audio_data: np.ndarray, sr: int) -> np.ndarray:
        try:
            import librosa
            y, _ = librosa.effects.trim(audio_data, top_db=20)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            return np.mean(mfcc, axis=1)
        except Exception:
            return np.zeros(13)
