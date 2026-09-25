import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmotionScores:
    reading_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    joy: float = 0.0
    sadness: float = 0.0
    anger: float = 0.0
    fear: float = 0.0
    disgust: float = 0.0
    surprise: float = 0.0
    neutral: float = 1.0
    timestamp: float = field(default_factory=time.time)


class EmotionDetectionService:
    def detect(self, multimodal_input: dict[str, Any]) -> dict[str, float]:
        scores = EmotionScores(
            joy=multimodal_input.get("joy", 0.0),
            sadness=multimodal_input.get("sadness", 0.0),
            anger=multimodal_input.get("anger", 0.0),
            fear=multimodal_input.get("fear", 0.0),
            disgust=multimodal_input.get("disgust", 0.0),
            surprise=multimodal_input.get("surprise", 0.0),
        )
        total = scores.joy + scores.sadness + scores.anger + scores.fear + scores.disgust + scores.surprise
        if total < 1.0:
            scores.neutral = max(0.0, 1.0 - total)
        result = {
            "joy": round(scores.joy, 3),
            "sadness": round(scores.sadness, 3),
            "anger": round(scores.anger, 3),
            "fear": round(scores.fear, 3),
            "disgust": round(scores.disgust, 3),
            "surprise": round(scores.surprise, 3),
            "neutral": round(scores.neutral, 3),
            "dominant": max(
                {"joy": scores.joy, "sadness": scores.sadness, "anger": scores.anger, "fear": scores.fear, "disgust": scores.disgust, "surprise": scores.surprise, "neutral": scores.neutral},
                key=lambda x: x[1],
            )[0],
        }
        logger.debug("Emotion detected: %s", result["dominant"])
        return result
