"""Video AI core package."""

from __future__ import annotations

from ASTROVOX_AI.ai_core.video.text_to_video import TextToVideoEngine, GeneratedVideo
from ASTROVOX_AI.ai_core.video.video_summarization import VideoSummarizationEngine, VideoSummary
from ASTROVOX_AI.ai_core.video.scene_detection import SceneDetectionEngine, SceneChange
from ASTROVOX_AI.ai_core.video.subtitle_generation import SubtitleGenerationEngine, SubtitleSegment
from ASTROVOX_AI.ai_core.video.lip_sync import LipSyncEngine, LipSyncResult
from ASTROVOX_AI.ai_core.video.motion_tracking import MotionTrackingEngine, TrackedObject
from ASTROVOX_AI.ai_core.video.frame_interpolation import FrameInterpolationEngine, InterpolatedVideo

__all__ = [
    "TextToVideoEngine",
    "GeneratedVideo",
    "VideoSummarizationEngine",
    "VideoSummary",
    "SceneDetectionEngine",
    "SceneChange",
    "SubtitleGenerationEngine",
    "SubtitleSegment",
    "LipSyncEngine",
    "LipSyncResult",
    "MotionTrackingEngine",
    "TrackedObject",
    "FrameInterpolationEngine",
    "InterpolatedVideo",
]
