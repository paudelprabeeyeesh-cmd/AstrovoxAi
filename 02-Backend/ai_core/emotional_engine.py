import numpy as np
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time


@dataclass
class EmotionState:
    valence: float
    arousal: float
    dominance: float
    label: str
    intensity: float = 1.0
    timestamp: float = field(default_factory=time.time)

    def vector(self) -> np.ndarray:
        return np.array([self.valence, self.arousal, self.dominance])


class EmotionalStimulus:
    def __init__(self, content: Any, valence: float, arousal: float, dominance: float, confidence: float = 1.0):
        self.content = content
        self.valence = valence
        self.arousal = arousal
        self.dominance = dominance
        self.confidence = confidence


class EmotionRecognizer:
    def __init__(self, feature_dim: int = 16):
        self.feature_dim = feature_dim
        self.valence_weights = np.random.randn(feature_dim) * 0.01
        self.arousal_weights = np.random.randn(feature_dim) * 0.01
        self.dominance_weights = np.random.randn(feature_dim) * 0.01

    def recognize(self, stimulus: EmotionalStimulus) -> EmotionState:
        if isinstance(stimulus.content, str):
            features = np.zeros(self.feature_dim)
            for i, ch in enumerate(stimulus.content[: self.feature_dim]):
                features[i] = (ord(ch) % 256) / 256.0
        elif isinstance(stimulus.content, dict):
            values = [float(v) for v in stimulus.content.values() if isinstance(v, (int, float))]
            arr = np.array(values[: self.feature_dim]) if values else np.zeros(self.feature_dim)
            features = np.pad(arr, (0, self.feature_dim - len(arr))) if len(arr) < self.feature_dim else arr[: self.feature_dim]
        else:
            features = np.random.randn(self.feature_dim) * 0.1
        valence = float(np.tanh(np.dot(self.valence_weights, features)))
        arousal = float(np.tanh(np.dot(self.arousal_weights, features)))
        dominance = float(np.tanh(np.dot(self.dominance_weights, features)))
        valence = valence * (1 - stimulus.confidence) + stimulus.valence * stimulus.confidence
        arousal = arousal * (1 - stimulus.confidence) + stimulus.arousal * stimulus.confidence
        dominance = dominance * (1 - stimulus.confidence) + stimulus.dominance * stimulus.confidence
        label = self._categorize(valence, arousal, dominance)
        return EmotionState(valence=valence, arousal=arousal, dominance=dominance, label=label, intensity=stimulus.confidence)

    def _categorize(self, valence: float, arousal: float, dominance: float) -> str:
        if valence > 0.3 and arousal > 0.3:
            return "joy"
        if valence > 0.3 and arousal < -0.3:
            return "contentment"
        if valence < -0.3 and dominance > 0.3 and arousal > 0.3:
            return "anger"
        if valence < -0.3 and arousal > 0.3:
            return "anger"
        if valence < -0.3 and arousal < -0.3:
            return "sadness"
        if arousal > 0.5 and abs(valence) <= 0.3:
            return "surprise"
        if valence < -0.2 and dominance < -0.2:
            return "fear"
        return "neutral"


class EmpathyModel:
    def __init__(self):
        self.observed_states: List[EmotionState] = []
        self.empathy_weights = np.array([0.4, 0.35, 0.25])

    def align(self, target: EmotionState) -> np.ndarray:
        vec = target.vector()
        self.observed_states.append(target)
        return vec * self.empathy_weights

    def emotional_contagion(self, source: EmotionState, target_current: EmotionState,
                            strength: float = 0.3) -> EmotionState:
        aligned = self.align(source)
        blended = (1 - strength) * target_current.vector() + strength * aligned
        label = self._categorize(*blended)
        return EmotionState(
            valence=float(blended[0]),
            arousal=float(blended[1]),
            dominance=float(blended[2]),
            label=label,
            intensity=target_current.intensity,
        )

    def _categorize(self, valence: float, arousal: float, dominance: float) -> str:
        if valence > 0.3 and arousal > 0.3:
            return "joy"
        if valence > 0.3 and arousal < -0.3:
            return "contentment"
        if valence < -0.3 and arousal > 0.3:
            return "anger"
        if valence < -0.3 and arousal < -0.3:
            return "sadness"
        if arousal > 0.5 and abs(valence) <= 0.3:
            return "surprise"
        if valence < -0.2 and dominance < -0.2:
            return "fear"
        return "neutral"


class EmotionalEngine:
    def __init__(self, feature_dim: int = 16):
        self.recognizer = EmotionRecognizer(feature_dim=feature_dim)
        self.empathy = EmpathyModel()
        self.current_state: Optional[EmotionState] = None
        self._history: List[EmotionState] = []

    def process_stimulus(self, content: Any, valence: float, arousal: float, dominance: float,
                         confidence: float = 1.0) -> EmotionState:
        stimulus = EmotionalStimulus(content=content, valence=valence, arousal=arousal,
                                     dominance=dominance, confidence=confidence)
        new_state = self.recognizer.recognize(stimulus)
        if self.current_state is not None:
            w = confidence
            blended = (1 - w) * self.current_state.vector() + w * new_state.vector()
            label = self.empathy._categorize(*blended)
            self.current_state = EmotionState(
                valence=float(blended[0]),
                arousal=float(blended[1]),
                dominance=float(blended[2]),
                label=label,
                intensity=max(self.current_state.intensity, new_state.intensity),
            )
        else:
            self.current_state = new_state
        self._history.append(self.current_state)
        return self.current_state

    def empathize(self, other: EmotionState) -> np.ndarray:
        return self.empathy.align(other)

    def get_emotional_profile(self) -> Dict[str, Any]:
        if self.current_state is None:
            return {"status": "no_data"}
        return {
            "current_emotion": self.current_state.label,
            "valence": self.current_state.valence,
            "arousal": self.current_state.arousal,
            "dominance": self.current_state.dominance,
            "intensity": self.current_state.intensity,
            "bias_vector": self.current_state.vector().tolist(),
        }
