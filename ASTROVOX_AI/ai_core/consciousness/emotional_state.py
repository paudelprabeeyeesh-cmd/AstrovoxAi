import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EmotionType(Enum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"


@dataclass
class EmotionalState:
    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.5
    emotions: dict[str, float] = field(default_factory=dict)
    regulation_strategy: str = "reappraisal"


class EmotionalStateEngine:
    def __init__(self):
        self.current_state = EmotionalState()
        self.emotion_history: list[dict[str, Any]] = []

    def generate_emotion(
        self, trigger: str, emotion_type: EmotionType, intensity: float = 1.0
    ) -> dict[str, Any]:
        emotion_name = emotion_type.value

        if emotion_type == EmotionType.JOY:
            self.current_state.valence = min(1.0, self.current_state.valence + intensity * 0.5)
            self.current_state.arousal = max(0.0, self.current_state.arousal - intensity * 0.2)
        elif emotion_type == EmotionType.ANGER:
            self.current_state.valence = max(-1.0, self.current_state.valence - intensity * 0.4)
            self.current_state.arousal = min(1.0, self.current_state.arousal + intensity * 0.6)
            self.current_state.dominance = min(1.0, self.current_state.dominance + intensity * 0.3)
        elif emotion_type == EmotionType.FEAR:
            self.current_state.valence = max(-1.0, self.current_state.valence - intensity * 0.5)
            self.current_state.arousal = min(1.0, self.current_state.arousal + intensity * 0.7)
            self.current_state.dominance = max(0.0, self.current_state.dominance - intensity * 0.4)

        self.current_state.emotions[emotion_name] = min(1.0, intensity)

        record = {
            "trigger": trigger,
            "emotion": emotion_name,
            "intensity": intensity,
            "valence": self.current_state.valence,
            "arousal": self.current_state.arousal,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.emotion_history.append(record)
        logger.info("Emotion generated: %s (intensity=%.2f)", emotion_name, intensity)
        return record

    def regulate(self, strategy: str) -> dict[str, Any]:
        self.current_state.regulation_strategy = strategy

        if strategy == "reappraisal":
            self.current_state.valence = self.current_state.valence * 0.8 + 0.1
            self.current_state.arousal = max(0.0, self.current_state.arousal - 0.2)
        elif strategy == "suppression":
            self.current_state.arousal = max(0.0, self.current_state.arousal - 0.4)
        elif strategy == "situation_selection":
            self.current_state.valence = min(1.0, self.current_state.valence + 0.3)

        logger.info("Emotion regulated with strategy: %s", strategy)
        return {"status": "regulated", "strategy": strategy, "new_valence": self.current_state.valence}

    def get_state(self) -> dict[str, Any]:
        return {
            "valence": self.current_state.valence,
            "arousal": self.current_state.arousal,
            "dominance": self.current_state.dominance,
            "active_emotions": self.current_state.emotions,
            "regulation_strategy": self.current_state.regulation_strategy,
            "history_length": len(self.emotion_history),
        }
