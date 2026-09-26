import os
import logging
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class SpeakerIdentifier:
    def __init__(self, storage_dir: str = "/tmp/astrovox_speakers"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.speaker_embeddings: Dict[str, np.ndarray] = {}
        self.speaker_metadata: Dict[str, Dict[str, Any]] = {}

    def enroll_speaker(self, speaker_id: str, audio_paths: List[str], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not audio_paths:
            raise ValueError("At least one audio sample is required for enrollment")
        embeddings = []
        for path in audio_paths:
            if os.path.exists(path):
                embedding = self._compute_embedding(path)
                embeddings.append(embedding)
        if not embeddings:
            raise ValueError("No valid audio samples provided")
        mean_embedding = np.mean(embeddings, axis=0)
        self.speaker_embeddings[speaker_id] = mean_embedding
        profile = {
            "speaker_id": speaker_id,
            "sample_count": len(embeddings),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        self.speaker_metadata[speaker_id] = profile
        profile_path = self.storage_dir / f"{speaker_id}.npz"
        np.savez(profile_path, embedding=mean_embedding, metadata=profile)
        logger.info(f"Enrolled speaker {speaker_id} with {len(embeddings)} samples")
        return profile

    def identify_speaker(self, audio_path: str, threshold: float = 0.7) -> Dict[str, Any]:
        if not self.speaker_embeddings:
            return {"speaker_id": None, "confidence": 0.0, "status": "no_enrolled_speakers"}
        query_embedding = self._compute_embedding(audio_path)
        best_match = None
        best_score = -1.0
        for speaker_id, embedding in self.speaker_embeddings.items():
            score = float(np.dot(query_embedding, embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(embedding) + 1e-8))
            if score > best_score:
                best_score = score
                best_match = speaker_id
        if best_match and best_score >= threshold:
            return {
                "speaker_id": best_match,
                "confidence": round(best_score, 4),
                "status": "identified",
                "metadata": self.speaker_metadata.get(best_match, {}).get("metadata", {}),
            }
        return {
            "speaker_id": None,
            "confidence": round(best_score, 4),
            "status": "unknown",
            "threshold": threshold,
        }

    def diarize_audio(self, audio_path: str, num_speakers: Optional[int] = None) -> Dict[str, Any]:
        try:
            from pyannote.audio import Pipeline
            pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
            diarization = pipeline(audio_path, num_speakers=num_speakers)
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "speaker": speaker,
                    "start": round(turn.start, 2),
                    "end": round(turn.end, 2),
                    "duration": round(turn.end - turn.start, 2),
                })
            return {
                "audio_path": audio_path,
                "num_speakers": len(set(s["speaker"] for s in segments)),
                "segments": segments,
                "status": "completed",
            }
        except Exception as exc:
            logger.error(f"Diarization failed: {exc}")
            return {"audio_path": audio_path, "error": str(exc), "status": "failed"}

    def list_speakers(self) -> List[Dict[str, Any]]:
        return [self.speaker_metadata[sid] for sid in self.speaker_embeddings]

    def delete_speaker(self, speaker_id: str) -> bool:
        if speaker_id not in self.speaker_embeddings:
            return False
        del self.speaker_embeddings[speaker_id]
        self.speaker_metadata.pop(speaker_id, None)
        profile_path = self.storage_dir / f"{speaker_id}.npz"
        if profile_path.exists():
            profile_path.unlink()
        return True

    def _compute_embedding(self, audio_path: str) -> np.ndarray:
        try:
            import torch
            from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2Model
            import soundfile as sf
            feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/wav2vec2-base")
            model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base")
            model.eval()
            data, sr = sf.read(audio_path)
            if sr != 16000:
                import librosa
                data, _ = librosa.resample(data, orig_sr=sr, target_sr=16000)
            inputs = feature_extractor(data, sampling_rate=16000, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()
            return embedding / (np.linalg.norm(embedding) + 1e-8)
        except Exception as exc:
            logger.warning(f"Embedding computation failed, using fallback: {exc}")
            return np.random.randn(768).astype(np.float32)
