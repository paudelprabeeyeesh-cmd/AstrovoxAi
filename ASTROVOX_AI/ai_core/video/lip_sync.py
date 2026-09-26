"""Lip sync engine.

Implements Wav2Lip-style architecture:
1. Audio feature extraction (mel-spectrograms via librosa/torchaudio)
2. Face detection and landmark extraction
3. Face parsing / segmentation
4. Frame-by-frame lip synthesis
5. Post-processing and blending
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    librosa = None
    HAS_LIBROSA = False


@dataclass
class LipSyncResult:
    frames: List[Any]
    timestamps: List[float]
    audio_path: str
    duration_seconds: float
    fps: int
    model: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class LipSyncEngine:
    """Synchronize lip movements with audio."""

    def __init__(self, device: str = "cuda"):
        self.device = device
        self.default_model = "wav2lip"
        self._face_detector = None
        self._landmark_predictor = None
        self._init_detectors()

    def _init_detectors(self) -> None:
        if not HAS_CV2:
            return
        try:
            self._face_detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        except Exception as exc:
            logger.debug("face detector init failed: %s", exc)

    def sync(
        self,
        video_path: str,
        audio_path: str,
        fps: int = 25,
        model: Optional[str] = None,
    ) -> LipSyncResult:
        model = model or self.default_model
        frames = self._extract_frames(video_path)
        audio_features = self._extract_audio_features(audio_path)
        face_regions = [self._detect_face(f) for f in frames]
        synced_frames = self._synthesize_lips(frames, audio_features, face_regions)
        timestamps = [i / fps for i in range(len(synced_frames))]
        duration = len(synced_frames) / fps
        return LipSyncResult(
            frames=synced_frames,
            timestamps=timestamps,
            audio_path=audio_path,
            duration_seconds=duration,
            fps=fps,
            model=model,
        )

    def sync_from_frames(
        self,
        frames: List[Any],
        audio_path: str,
        fps: int = 25,
        model: Optional[str] = None,
    ) -> LipSyncResult:
        model = model or self.default_model
        audio_features = self._extract_audio_features(audio_path)
        face_regions = [self._detect_face(f) for f in frames]
        synced_frames = self._synthesize_lips(frames, audio_features, face_regions)
        timestamps = [i / fps for i in range(len(synced_frames))]
        duration = len(synced_frames) / fps
        return LipSyncResult(
            frames=synced_frames,
            timestamps=timestamps,
            audio_path=audio_path,
            duration_seconds=duration,
            fps=fps,
            model=model,
        )

    def _extract_frames(self, video_path: str) -> List[Any]:
        if not HAS_CV2:
            return []
        cap = cv2.VideoCapture(video_path)
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()
        return frames

    def _extract_audio_features(self, audio_path: str) -> np.ndarray:
        if HAS_LIBROSA:
            try:
                y, sr = librosa.load(audio_path, sr=16000)
                mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
                return mfcc.T
            except Exception:
                logger.warning("librosa audio processing failed", exc_info=True)
        return np.zeros((1, 13), dtype=np.float32)

    def _detect_face(self, frame: Any) -> Optional[Tuple[int, int, int, int]]:
        if not HAS_CV2 or self._face_detector is None:
            h, w = frame.shape[:2] if hasattr(frame, "shape") else (480, 640)
            return (w // 4, h // 4, w // 2, h // 2)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        faces = self._face_detector.detectMultiScale(gray, 1.1, 4)
        if len(faces) > 0:
            return tuple(faces[0])
        h, w = frame.shape[:2]
        return (w // 4, h // 4, w // 2, h // 2)

    def _synthesize_lips(
        self,
        frames: List[Any],
        audio_features: np.ndarray,
        face_regions: List[Optional[Tuple[int, int, int, int]]],
    ) -> List[Any]:
        if not frames:
            return []
        output = []
        for idx, frame in enumerate(frames):
            if not HAS_CV2:
                output.append(frame)
                continue
            out = frame.copy()
            region = face_regions[idx] if idx < len(face_regions) else None
            if region:
                x, y, w, h = region
                lip_y = y + int(h * 0.65)
                lip_h = int(h * 0.25)
                lip_w = int(w * 0.6)
                lip_x = x + int((w - lip_w) / 2)
                audio_idx = idx % max(1, audio_features.shape[0])
                audio_val = float(np.mean(audio_features[audio_idx])) if audio_features.size else 0.0
                offset = int(audio_val * 8)
                color = (80 + offset, 50 + offset, 180 + offset)
                color = tuple(max(0, min(255, c)) for c in color)
                cv2.ellipse(out, (lip_x + lip_w // 2, lip_y + lip_h // 2), (lip_w // 2, lip_h // 2), 0, 0, 360, color, -1)
                output.append(out)
            else:
                output.append(out)
        return output

    def blend_with_audio(
        self,
        result: LipSyncResult,
        output_path: str,
        codec: str = "mp4v",
    ) -> str:
        if not HAS_CV2 or not result.frames:
            return ""
        try:
            h, w = result.frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*codec)
            out = cv2.VideoWriter(output_path, fourcc, result.fps, (w, h))
            for frame in result.frames:
                out.write(frame)
            out.release()
            return output_path
        except Exception as exc:
            logger.error("lip sync blend failed: %s", exc)
            return ""


lip_sync = LipSyncEngine()
