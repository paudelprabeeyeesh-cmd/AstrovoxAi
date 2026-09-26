"""Video AI service layer.

Orchestrates video processing features:
- text-to-video
- video summarization
- scene detection
- subtitle generation
- lip sync
- motion tracking
- frame interpolation
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ASTROVOX_AI.ai_core.video import (
    FrameInterpolationEngine,
    LipSyncEngine,
    MotionTrackingEngine,
    SceneDetectionEngine,
    SubtitleGenerationEngine,
    TextToVideoEngine,
    VideoSummarizationEngine,
)

logger = logging.getLogger(__name__)


@dataclass
class VideoJob:
    job_id: str
    feature: str
    status: str
    input_path: str
    output_path: str
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


class VideoAIService:
    """Service layer for video AI operations."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or os.getenv("ASTROVOX_VIDEO_DIR", "./storage/video")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.text_to_video = TextToVideoEngine()
        self.summarization = VideoSummarizationEngine()
        self.scene_detection = SceneDetectionEngine()
        self.subtitles = SubtitleGenerationEngine()
        self.lip_sync = LipSyncEngine()
        self.motion_tracking = MotionTrackingEngine()
        self.frame_interpolation = FrameInterpolationEngine()
        self._jobs: Dict[str, VideoJob] = {}

    def _save_upload(self, content: bytes, suffix: str = ".mp4") -> str:
        path = os.path.join(self.storage_dir, f"{uuid.uuid4().hex}{suffix}")
        with open(path, "wb") as f:
            f.write(content)
        return path

    def text_to_video(
        self,
        prompt: str,
        image_base64: Optional[str] = None,
        duration_seconds: float = 4.0,
        width: int = 1024,
        height: int = 576,
        fps: int = 24,
        model: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        try:
            videos = self.text_to_video.generate(
                prompt=prompt,
                image=image_base64,
                duration_seconds=duration_seconds,
                width=width,
                height=height,
                fps=fps,
                model=model,
                seed=seed,
            )
            results = []
            for v in videos:
                results.append({
                    "url": v.url,
                    "prompt": v.prompt,
                    "duration_seconds": v.duration_seconds,
                    "width": v.width,
                    "height": v.height,
                    "fps": v.fps,
                    "frames": v.frames,
                    "model": v.model,
                    "seed": v.seed,
                    "metadata": v.metadata,
                })
            return {"job_id": job_id, "status": "completed", "videos": results}
        except Exception as exc:
            logger.error("text-to-video failed: %s", exc)
            return {"job_id": job_id, "status": "failed", "error": str(exc), "videos": []}

    def summarize(
        self,
        video_bytes: bytes,
        prompt: str = "Summarize the key events and content in this video.",
        max_scenes: int = 5,
    ) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        path = self._save_upload(video_bytes)
        try:
            summary = self.summarization.summarize(path, prompt=prompt, max_scenes=max_scenes)
            return {
                "job_id": job_id,
                "status": "completed",
                "summary": summary.summary,
                "key_frames": summary.key_frames,
                "scene_count": summary.scene_count,
                "duration_seconds": summary.duration_seconds,
                "model": summary.model,
            }
        except Exception as exc:
            logger.error("summarization failed: %s", exc)
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def detect_scenes(
        self,
        video_bytes: bytes,
        threshold: float = 0.3,
        method: str = "histogram",
    ) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        path = self._save_upload(video_bytes)
        try:
            scenes = self.scene_detection.detect(path, threshold=threshold, method=method)
            stats = self.scene_detection.get_scene_statistics(path, threshold=threshold)
            return {
                "job_id": job_id,
                "status": "completed",
                "scenes": [
                    {"frame_index": s.frame_index, "timestamp": s.timestamp, "score": s.score, "method": s.method}
                    for s in scenes
                ],
                "statistics": stats,
            }
        except Exception as exc:
            logger.error("scene detection failed: %s", exc)
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def generate_subtitles(
        self,
        video_bytes: bytes,
        language: Optional[str] = None,
        format: str = "srt",
    ) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        path = self._save_upload(video_bytes, suffix=".mp4")
        audio_path = None
        try:
            segments = self.subtitles.generate_from_video(path, language=language)
            text_out = ""
            if format == "srt":
                text_out = self.subtitles.to_srt(segments)
            elif format == "vtt":
                text_out = self.subtitles.to_vtt(segments)
            elif format == "ass":
                text_out = self.subtitles.to_ass(segments)
            else:
                text_out = json.dumps([s.__dict__ for s in segments], indent=2)
            return {
                "job_id": job_id,
                "status": "completed",
                "segments": [s.__dict__ for s in segments],
                "format": format,
                "content": text_out,
            }
        except Exception as exc:
            logger.error("subtitle generation failed: %s", exc)
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
            if audio_path:
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

    def lip_sync(
        self,
        video_bytes: bytes,
        audio_bytes: bytes,
        fps: int = 25,
    ) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        video_path = self._save_upload(video_bytes, suffix=".mp4")
        audio_path = self._save_upload(audio_bytes, suffix=".wav")
        output_path = os.path.join(self.storage_dir, f"{job_id}_output.mp4")
        try:
            result = self.lip_sync.sync(video_path, audio_path, fps=fps)
            saved = self.lip_sync.blend_with_audio(result, output_path)
            timestamps = [{"time": t, "frame": idx} for idx, t in enumerate(result.timestamps[:50])]
            return {
                "job_id": job_id,
                "status": "completed",
                "output_path": saved,
                "duration_seconds": result.duration_seconds,
                "fps": result.fps,
                "model": result.model,
                "timestamps": timestamps,
            }
        except Exception as exc:
            logger.error("lip sync failed: %s", exc)
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
        finally:
            for p in (video_path, audio_path):
                try:
                    os.remove(p)
                except OSError:
                    pass

    def track_motion(
        self,
        video_bytes: bytes,
        init_bbox: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        path = self._save_upload(video_bytes)
        try:
            if init_bbox:
                bbox = (init_bbox["x"], init_bbox["y"], init_bbox["width"], init_bbox["height"])
                tracked = self.motion_tracking.track(path, bbox, label="user_object")
                trajectory = self.motion_tracking.compute_trajectory(tracked)
                velocity = self.motion_tracking.compute_velocity(tracked)
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "object_id": tracked.object_id,
                    "label": tracked.label,
                    "bboxes": [list(b) for b in tracked.bboxes],
                    "timestamps": tracked.timestamps,
                    "scores": tracked.scores,
                    "trajectory": [{"x": x, "y": y} for x, y in trajectory],
                    "velocity": velocity,
                }
            objects = self.motion_tracking.track_all(path)
            results = []
            for obj in objects:
                traj = self.motion_tracking.compute_trajectory(obj)
                vel = self.motion_tracking.compute_velocity(obj)
                results.append({
                    "object_id": obj.object_id,
                    "label": obj.label,
                    "bbox_count": len(obj.bboxes),
                    "timestamps": obj.timestamps,
                    "trajectory": [{"x": x, "y": y} for x, y in traj],
                    "velocity": vel,
                })
            return {"job_id": job_id, "status": "completed", "objects": results}
        except Exception as exc:
            logger.error("motion tracking failed: %s", exc)
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def interpolate(
        self,
        video_bytes: bytes,
        multiplier: int = 2,
        method: str = "flow",
    ) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex[:12]
        path = self._save_upload(video_bytes)
        output_path = os.path.join(self.storage_dir, f"{job_id}_interpolated.mp4")
        try:
            result = self.frame_interpolation.interpolate(path, multiplier=multiplier, method=method)
            saved = self.frame_interpolation.save_video(result, output_path)
            return {
                "job_id": job_id,
                "status": "completed",
                "original_fps": result.original_fps,
                "target_fps": result.target_fps,
                "output_frames": len(result.frames),
                "duration_seconds": result.duration_seconds,
                "method": result.method,
                "output_path": saved,
            }
        except Exception as exc:
            logger.error("frame interpolation failed: %s", exc)
            return {"job_id": job_id, "status": "failed", "error": str(exc)}
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def job_status(self, job_id: str) -> Dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            return {"job_id": job_id, "status": "unknown"}
        return {
            "job_id": job.job_id,
            "feature": job.feature,
            "status": job.status,
            "input_path": job.input_path,
            "output_path": job.output_path,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at,
        }


video_ai = VideoAIService()
