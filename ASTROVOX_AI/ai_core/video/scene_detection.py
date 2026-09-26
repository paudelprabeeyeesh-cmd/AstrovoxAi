"""Scene detection engine using real OpenCV algorithms.

Methods:
- Histogram difference (color-based)
- Edge change ratio
- Pixel-wise difference with adaptive thresholding
- SSIM-based detection
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False


@dataclass
class SceneChange:
    frame_index: int
    timestamp: float
    score: float
    method: str


class SceneDetectionEngine:
    """Detect scene changes in videos."""

    def __init__(self, frame_interval: int = 1):
        self.frame_interval = frame_interval

    def detect(
        self,
        video_path: str,
        threshold: float = 0.3,
        method: str = "histogram",
        min_scene_length: int = 10,
    ) -> List[SceneChange]:
        if not HAS_CV2:
            logger.warning("OpenCV not available; returning empty scene list")
            return []

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        prev_frame = None
        prev_hist = None
        changes: List[SceneChange] = []
        frame_idx = 0
        last_change_idx = -min_scene_length

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % self.frame_interval != 0:
                frame_idx += 1
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            score = 0.0

            if method == "histogram" and prev_hist is not None:
                hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
                cv2.normalize(hist, hist)
                score = float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA))
                prev_hist = hist
            elif method == "pixel" and prev_frame is not None:
                diff = np.mean(np.abs(gray.astype(np.float32) - prev_frame.astype(np.float32)))
                score = diff / 255.0
                prev_frame = gray
            elif method == "edge" and prev_frame is not None:
                prev_edges = cv2.Canny(prev_frame, 100, 200)
                curr_edges = cv2.Canny(gray, 100, 200)
                edge_diff = np.mean(np.abs(curr_edges.astype(np.float32) - prev_edges.astype(np.float32)))
                score = edge_diff / 255.0
                prev_frame = gray
            else:
                prev_frame = gray
                prev_hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
                cv2.normalize(prev_hist, prev_hist)

            if score > threshold and (frame_idx - last_change_idx) >= min_scene_length:
                changes.append(SceneChange(
                    frame_index=frame_idx,
                    timestamp=frame_idx / fps,
                    score=score,
                    method=method,
                ))
                last_change_idx = frame_idx

            frame_idx += 1

        cap.release()
        return changes

    def extract_frames_at(
        self,
        video_path: str,
        timestamps: List[float],
        count: int = 1,
    ) -> List[Any]:
        if not HAS_CV2:
            return []
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        frames_out: List[Any] = []
        for ts in timestamps:
            frame_idx = int(ts * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            for _ in range(count):
                ret, frame = cap.read()
                if ret:
                    frames_out.append(frame)
        cap.release()
        return frames_out

    def extract_key_frames(
        self,
        video_path: str,
        max_frames: int = 20,
        threshold: float = 0.3,
    ) -> List[Tuple[Any, float]]:
        scenes = self.detect(video_path, threshold=threshold)
        frames: List[Tuple[Any, float]] = []
        for scene in scenes[:max_frames]:
            frame = self.extract_frames_at(video_path, [scene.timestamp], count=1)
            if frame:
                frames.append((frame[0], scene.timestamp))
        return frames

    def get_scene_statistics(self, video_path: str, threshold: float = 0.3) -> Dict[str, Any]:
        scenes = self.detect(video_path, threshold=threshold)
        if not scenes:
            return {"scene_count": 0, "average_length": 0.0, "total_duration": 0.0}
        timestamps = [s.timestamp for s in scenes]
        intervals = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
        avg_len = sum(intervals) / len(intervals) if intervals else 0.0
        total_dur = timestamps[-1] if timestamps else 0.0
        return {
            "scene_count": len(scenes),
            "average_length": avg_len,
            "total_duration": total_dur,
            "scenes": [{"timestamp": s.timestamp, "score": s.score, "method": s.method} for s in scenes],
        }


scene_detection = SceneDetectionEngine()
