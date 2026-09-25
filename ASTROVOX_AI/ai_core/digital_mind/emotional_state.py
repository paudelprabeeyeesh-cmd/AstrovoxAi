from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EmotionalState:
    joy: float = 0.0
    sadness: float = 0.0
    anger: float = 0.0
    fear: float = 0.0
    surprise: float = 0.0
    disgust: float = 0.0
    trust: float = 0.0
    anticipation: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def normalize(self):
        total = sum(
            [
                self.joy,
                self.sadness,
                self.anger,
                self.fear,
                self.surprise,
                self.disgust,
                self.trust,
                self.anticipation,
            ]
        )
        if total > 0:
            self.joy /= total
            self.sadness /= total
            self.anger /= total
            self.fear /= total
            self.surprise /= total
            self.disgust /= total
            self.trust /= total
            self.anticipation /= total


class EmotionalStateModeling:
    def __init__(self, decay_rate: float = 0.05):
        self.current_state = EmotionalState()
        self.history: list[EmotionalState] = []
        self.decay_rate = decay_rate
        self.mood_baseline: dict[str, float] = {}

    def update_emotion(self, emotion: str, delta: float):
        if hasattr(self.current_state, emotion):
            setattr(self.current_state, emotion, max(0.0, min(1.0, getattr(self.current_state, emotion) + delta)))
        self.current_state.normalize()
        self.history.append(self.current_state)
        if len(self.history) > 500:
            self.history = self.history[-500:]

    def decay(self):
        for attr in [
            "joy",
            "sadness",
            "anger",
            "fear",
            "surprise",
            "disgust",
            "trust",
            "anticipation",
        ]:
            val = getattr(self.current_state, attr)
            setattr(self.current_state, attr, max(0.0, val - self.decay_rate))

    def dominant_emotion(self) -> str:
        emotions = {
            "joy": self.current_state.joy,
            "sadness": self.current_state.sadness,
            "anger": self.current_state.anger,
            "fear": self.current_state.fear,
            "surprise": self.current_state.surprise,
            "disgust": self.current_state.disgust,
            "trust": self.current_state.trust,
            "anticipation": self.current_state.anticipation,
        }
        if not emotions:
            return "neutral"
        return max(emotions, key=emotions.get)

    def get_state_summary(self) -> dict[str, Any]:
        return {
            "dominant": self.dominant_emotion(),
            "joy": self.current_state.joy,
            "sadness": self.current_state.sadness,
            "anger": self.current_state.anger,
            "fear": self.current_state.fear,
            "trust": self.current_state.trust,
            "history_length": len(self.history),
        }
