import logging
from typing import Any

logger = logging.getLogger(__name__)


class EmotionDetectionService:
    def detect(self, multimodal_input: dict[str, Any]) -> dict[str, float]:
        return {"joy": 0.0, "sadness": 0.0, "anger": 0.0, "fear": 0.0, "surprise": 0.0, "neutral": 1.0}
