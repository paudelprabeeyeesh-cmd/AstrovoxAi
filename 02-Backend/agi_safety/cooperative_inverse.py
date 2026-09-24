import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Preference:
    context: str
    preferred_action: int
    dispreferred_action: int
    confidence: float


@dataclass
class ValueEstimate:
    state: np.ndarray
    action_values: np.ndarray
    preferred_action: int
    confidence: float


class PreferenceLearning:
    def __init__(self, state_dim: int, num_actions: int, learning_rate: float = 0.1):
        self.state_dim = state_dim
        self.num_actions = num_actions
        self.learning_rate = learning_rate
        rng = np.random.RandomState(42)
        self.weights = rng.randn(state_dim, num_actions) * 0.01
        self.preferences: List[Preference] = []

    def observe_preference(self, state: np.ndarray, preferred: int, dispreferred: int, confidence: float) -> None:
        pref = Preference(
            context=str(state.tolist()),
            preferred_action=preferred,
            dispreferred_action=dispreferred,
            confidence=confidence,
        )
        self.preferences.append(pref)
        self._update_weights(state, preferred, dispreferred, confidence)

    def _update_weights(self, state: np.ndarray, preferred: int, dispreferred: int, confidence: float) -> None:
        q_pref = state @ self.weights[:, preferred]
        q_dis = state @ self.weights[:, dispreferred]
        margin = q_pref - q_dis
        if margin < 1.0:
            grad = np.outer(state, -np.eye(self.num_actions)[preferred] + np.eye(self.num_actions)[dispreferred])
            self.weights -= self.learning_rate * confidence * grad

    def estimate_value(self, state: np.ndarray) -> ValueEstimate:
        q = state @ self.weights
        preferred = int(np.argmax(q))
        confidence = float(np.max(q) / (np.sum(np.abs(q)) + 1e-9))
        return ValueEstimate(
            state=state.copy(),
            action_values=q.copy(),
            preferred_action=preferred,
            confidence=round(confidence, 4),
        )

    def get_preference_stats(self) -> Dict:
        if not self.preferences:
            return {"total": 0, "avg_confidence": 0.0}
        total = len(self.preferences)
        avg_conf = np.mean([p.confidence for p in self.preferences])
        return {"total": total, "avg_confidence": round(float(avg_conf), 4)}


class CooperativeInverseRL:
    def __init__(self, state_dim: int, num_actions: int):
        self.value_learner = PreferenceLearning(state_dim, num_actions)
        self.human_feedback: List[Dict] = []

    def propose_action(self, state: np.ndarray) -> int:
        return self.value_learner.estimate_value(state).preferred_action

    def receive_feedback(self, state: np.ndarray, action: int, feedback: str) -> None:
        feedback_str = feedback.lower()
        is_positive = "good" in feedback_str or "yes" in feedback_str or "correct" in feedback_str
        is_negative = "bad" in feedback_str or "no" in feedback_str or "incorrect" in feedback_str
        if is_positive:
            self.value_learner.observe_preference(state, action, (action + 1) % self.value_learner.num_actions, 0.9)
        elif is_negative:
            self.value_learner.observe_preference(state, (action + 1) % self.value_learner.num_actions, action, 0.9)
        self.human_feedback.append({"state": state.tolist(), "action": action, "feedback": feedback})

    def get_alignment_metrics(self) -> Dict:
        pref_stats = self.value_learner.get_preference_stats()
        return {
            "total_feedback": len(self.human_feedback),
            "positive_rate": round(sum(1 for f in self.human_feedback if "good" in f["feedback"].lower()) / max(len(self.human_feedback), 1), 4),
            **pref_stats,
        }
