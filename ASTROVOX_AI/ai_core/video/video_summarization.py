"""Video summarization engine.

Produces concise summaries of video content by:
1. Extracting key frames via scene detection
2. Scoring frames using visual features
3. Generating text summaries via LLM or extractive methods
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ASTROVOX_AI.ai_core.video.scene_detection import SceneDetectionEngine, SceneChange

logger = logging.getLogger(__name__)


@dataclass
class VideoSummary:
    summary: str
    key_frames: List[Dict[str, Any]]
    scene_count: int
    duration_seconds: float
    model: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class VideoSummarizationEngine:
    """Summarize video content."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.default_model = "gpt-4o"
        self._client = None
        try:
            import httpx
            self._client = httpx.Client(timeout=60.0)
        except ImportError:
            logger.debug("httpx not available")

    def summarize(
        self,
        video_path: str,
        prompt: str = "Summarize the key events and content in this video.",
        max_scenes: int = 5,
        max_frames_per_scene: int = 3,
    ) -> VideoSummary:
        scene_engine = SceneDetectionEngine()
        scenes = scene_engine.detect(video_path, threshold=0.4)
        scene_count = len(scenes)

        key_frames = []
        for i, scene in enumerate(scenes[:max_scenes]):
            frames = scene_engine.extract_frames_at(video_path, [scene.timestamp], count=max_frames_per_scene)
            for j, frame in enumerate(frames):
                key_frames.append({
                    "scene_index": i,
                    "frame_index": j,
                    "timestamp": scene.timestamp,
                    "score": scene.score,
                    "image_base64": self._frame_to_base64(frame),
                })

        summary_text = self._generate_summary(prompt, key_frames, scene_count)
        duration = self._get_duration(video_path)
        return VideoSummary(
            summary=summary_text,
            key_frames=key_frames,
            scene_count=scene_count,
            duration_seconds=duration,
            model=self.default_model,
        )

    def summarize_by_frames(
        self,
        frames: List[Tuple[Any, float]],
        prompt: str = "Summarize the visual content.",
        max_frames: int = 10,
    ) -> VideoSummary:
        selected = frames[:max_frames]
        key_frames = []
        for idx, (frame, ts) in enumerate(selected):
            key_frames.append({
                "frame_index": idx,
                "timestamp": ts,
                "image_base64": self._frame_to_base64(frame),
            })
        summary_text = self._generate_summary(prompt, key_frames, len(selected))
        return VideoSummary(
            summary=summary_text,
            key_frames=key_frames,
            scene_count=len(selected),
            duration_seconds=selected[-1][1] if selected else 0.0,
            model=self.default_model,
        )

    def extract_chapters(
        self,
        video_path: str,
        max_chapters: int = 10,
    ) -> List[Dict[str, Any]]:
        scene_engine = SceneDetectionEngine()
        scenes = scene_engine.detect(video_path, threshold=0.35)
        chapters = []
        for idx, scene in enumerate(scenes[:max_chapters]):
            chapters.append({
                "chapter": idx + 1,
                "timestamp": scene.timestamp,
                "score": scene.score,
                "frame_base64": self._frame_to_base64(
                    scene_engine.extract_frames_at(video_path, [scene.timestamp], count=1)[0]
                ),
            })
        return chapters

    def _generate_summary(self, prompt: str, key_frames: List[Dict[str, Any]], scene_count: int) -> str:
        if self._client and self.api_key:
            return self._llm_summary(prompt, key_frames, scene_count)
        return self._extractive_summary(key_frames, scene_count)

    def _llm_summary(self, prompt: str, key_frames: List[Dict[str, Any]], scene_count: int) -> str:
        try:
            messages = [{"role": "user", "content": prompt}]
            for kf in key_frames[:5]:
                img_data = kf.get("image_base64", "")
                if img_data:
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Frame at {kf.get('timestamp', 0):.1f}s"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}},
                        ],
                    })
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {"model": self.default_model, "messages": messages, "max_tokens": 500}
            response = self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.error("LLM summary failed: %s", exc)
            return self._extractive_summary(key_frames, scene_count)

    def _extractive_summary(self, key_frames: List[Dict[str, Any]], scene_count: int) -> str:
        if not key_frames:
            return "No content available for summarization."
        parts = []
        for kf in key_frames[:5]:
            ts = kf.get("timestamp", 0.0)
            score = kf.get("score", 0.0)
            parts.append(f"Key moment at {ts:.1f}s (importance: {score:.2f})")
        return (
            f"Video contains {scene_count} detected scenes. "
            f"Key moments: {'; '.join(parts)}. "
            "Enable an LLM API key for richer narrative summaries."
        )

    def _frame_to_base64(self, frame: Any) -> str:
        try:
            import cv2
            _, buf = cv2.imencode(".jpg", frame)
            return base64.b64encode(buf).decode("utf-8")
        except Exception:
            return ""

    def _get_duration(self, video_path: str) -> float:
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            fps_val = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            if fps_val > 0 and frame_count > 0:
                return frame_count / fps_val
        except Exception:
            pass
        return 0.0


video_summarization = VideoSummarizationEngine()
