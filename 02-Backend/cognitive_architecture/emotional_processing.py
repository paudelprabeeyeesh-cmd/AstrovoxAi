import numpy as np
from typing import List, Dict, Any, Optional
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

    def to_vector(self) -> np.ndarray:
        return np.array([self.valence, self.arousal, self.dominance])

    def decay(self, rate: float = 0.01) -> None:
        self.intensity *= np.exp(-rate)
        self.timestamp = time.time()


@dataclass
class EmotionalStimulus:
    content: Any
    valence: float
    arousal: float
    dominance: float
    confidence: float
    source: str = "unknown"


class EmotionRecognizer:
    def __init__(self, feature_dim: int = 16):
        self.feature_dim = feature_dim
        self.valence_weights = np.random.randn(feature_dim) * 0.01
        self.arousal_weights = np.random.randn(feature_dim) * 0.01
        self.dominance_weights = np.random.randn(feature_dim) * 0.01
        self._trained = False

    def extract_features(self, stimulus: Any) -> np.ndarray:
        if isinstance(stimulus, str):
            features = np.zeros(self.feature_dim)
            for i, char in enumerate(stimulus[: self.feature_dim]):
                features[i] = (ord(char) % 256) / 256.0
            return features
        if isinstance(stimulus, dict):
            values = [float(v) for v in stimulus.values() if isinstance(v, (int, float))]
            if not values:
                return np.zeros(self.feature_dim)
            arr = np.array(values)
            if len(arr) >= self.feature_dim:
                return arr[: self.feature_dim]
            padded = np.zeros(self.feature_dim)
            padded[: len(arr)] = arr
            return padded
        return np.random.randn(self.feature_dim) * 0.1

    def recognize(self, stimulus: EmotionalStimulus) -> EmotionState:
        features = self.extract_features(stimulus.content)
        valence = float(np.tanh(np.dot(self.valence_weights, features)))
        arousal = float(np.tanh(np.dot(self.arousal_weights, features)))
        dominance = float(np.tanh(np.dot(self.dominance_weights, features)))
        valence = valence * (1.0 - stimulus.confidence) + stimulus.valence * stimulus.confidence
        arousal = arousal * (1.0 - stimulus.confidence) + stimulus.arousal * stimulus.confidence
        dominance = dominance * (1.0 - stimulus.confidence) + stimulus.dominance * stimulus.confidence
        label = self._categorize(valence, arousal, dominance)
        return EmotionState(
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            label=label,
            intensity=stimulus.confidence,
        )

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

    def train_step(self, features: np.ndarray, target_valence: float, target_arousal: float,
                   target_dominance: float, lr: float = 0.001) -> float:
        pred_valence = np.tanh(np.dot(self.valence_weights, features))
        pred_arousal = np.tanh(np.dot(self.arousal_weights, features))
        pred_dominance = np.tanh(np.dot(self.dominance_weights, features))
        loss = (
            (pred_valence - target_valence) ** 2
            + (pred_arousal - target_arousal) ** 2
            + (pred_dominance - target_dominance) ** 2
        ) / 3.0
        self.valence_weights -= lr * (pred_valence - target_valence) * (1 - pred_valence ** 2) * features
        self.arousal_weights -= lr * (pred_arousal - target_arousal) * (1 - pred_arousal ** 2) * features
        self.dominance_weights -= lr * (pred_dominance - target_dominance) * (1 - pred_dominance ** 2) * features
        self._trained = True
        return float(loss)


class AffectiveState:
    def __init__(self, decay_rate: float = 0.01):
        self.current_state: Optional[EmotionState] = None
        self.decay_rate = decay_rate
        self._history: List[EmotionState] = []

    def update(self, stimulus: EmotionalStimulus, recognizer: EmotionRecognizer) -> EmotionState:
        new_state = recognizer.recognize(stimulus)
        if self.current_state is not None:
            w_new = stimulus.confidence
            self.current_state.valence = (1 - w_new) * self.current_state.valence + w_new * new_state.valence
            self.current_state.arousal = (1 - w_new) * self.current_state.arousal + w_new * new_state.arousal
            self.current_state.dominance = (1 - w_new) * self.current_state.dominance + w_new * new_state.dominance
            self.current_state.label = new_state.label
            self.current_state.intensity = max(self.current_state.intensity, new_state.intensity)
        else:
            self.current_state = new_state
        self.current_state.decay(self.decay_rate)
        self._history.append(self.current_state)
        return self.current_state

    def get_affective_bias(self) -> np.ndarray:
        if self.current_state is None:
            return np.zeros(3)
        return self.current_state.to_vector() * self.current_state.intensity

    def get_history(self) -> List[Dict[str, float]]:
        return [
            {
                "valence": e.valence,
                "arousal": e.arousal,
                "dominance": e.dominance,
                "intensity": e.intensity,
                "label": e.label,
            }
            for e in self._history[-50:]
        ]


class EmotionalProcessingSystem:
    def __init__(self, feature_dim: int = 16):
        self.recognizer = EmotionRecognizer(feature_dim=feature_dim)
        self.affective_state = AffectiveState()
        self._stimulus_log: List[EmotionalStimulus] = []

    def process_stimulus(self, content: Any, valence: float, arousal: float, dominance: float,
                         confidence: float = 1.0, source: str = "unknown") -> EmotionState:
        stimulus = EmotionalStimulus(
            content=content,
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            confidence=confidence,
            source=source,
        )
        self._stimulus_log.append(stimulus)
        return self.affective_state.update(stimulus, self.recognizer)

    def get_emotional_profile(self) -> Dict[str, Any]:
        state = self.affective_state.current_state
        if state is None:
            return {"status": "no_data"}
        return {
            "current_emotion": state.label,
            "valence": state.valence,
            "arousal": state.arousal,
            "dominance": state.dominance,
            "intensity": state.intensity,
            "bias_vector": self.affective_state.get_affective_bias().tolist(),
        }
