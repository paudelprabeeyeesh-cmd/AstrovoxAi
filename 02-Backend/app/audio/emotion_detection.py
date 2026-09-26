import os
import uuid
import logging
import tempfile
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class EmotionDetector:
    def __init__(self, model_name: str = "superb/wav2vec2-base-superb-er"):
        self.model_name = model_name
        self.processed: Dict[str, Dict[str, Any]] = {}
        self.temp_dir = Path(tempfile.gettempdir()) / "astrovox_emotion"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.emotion_labels = ["angry", "calm", "disgust", "fearful", "happy", "neutral", "sad", "surprised"]

    def detect(self, audio_path: str, segment_duration: float = 5.0) -> Dict[str, Any]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        try:
            import librosa
            import numpy as np
            from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
            import torch
            feature_extractor = AutoFeatureExtractor.from_pretrained(self.model_name)
            model = AutoModelForAudioClassification.from_pretrained(self.model_name)
            model.eval()
            y, sr = librosa.load(audio_path, sr=16000, mono=True)
            segment_samples = int(segment_duration * sr)
            segments_results = []
            for i in range(0, len(y), segment_samples):
                segment = y[i : i + segment_samples]
                if len(segment) < segment_samples // 2:
                    continue
                inputs = feature_extractor(segment, sampling_rate=16000, return_tensors="pt")
                with torch.no_grad():
                    outputs = model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
                pred_idx = int(torch.argmax(probs, dim=-1).item())
                confidence = float(probs[0, pred_idx].item())
                label = self.emotion_labels[pred_idx] if pred_idx < len(self.emotion_labels) else "unknown"
                segments_results.append({
                    "start": round(i / sr, 2),
                    "end": round((i + len(segment)) / sr, 2),
                    "emotion": label,
                    "confidence": round(confidence, 4),
                    "all_probs": {self.emotion_labels[j]: round(float(probs[0, j].item()), 4) for j in range(len(self.emotion_labels))},
                })
            dominant = self._aggregate_emotions(segments_results)
            result = {
                "audio_path": audio_path,
                "dominant_emotion": dominant["emotion"],
                "dominant_confidence": dominant["confidence"],
                "segments": segments_results,
                "status": "completed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.processed[audio_path] = result
            return result
        except Exception as exc:
            logger.error(f"Emotion detection failed: {exc}")
            return {"audio_path": audio_path, "error": str(exc), "status": "failed"}

    def detect_batch(self, audio_paths: List[str], segment_duration: float = 5.0) -> List[Dict[str, Any]]:
        return [self.detect(path, segment_duration) for path in audio_paths]

    def _aggregate_emotions(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not segments:
            return {"emotion": "neutral", "confidence": 0.0}
        emotion_scores: Dict[str, float] = {}
        for seg in segments:
            emotion = seg.get("emotion", "neutral")
            confidence = seg.get("confidence", 0.0)
            emotion_scores[emotion] = emotion_scores.get(emotion, 0.0) + confidence
        dominant = max(emotion_scores, key=emotion_scores.get)
        return {"emotion": dominant, "confidence": round(emotion_scores[dominant], 4)}
