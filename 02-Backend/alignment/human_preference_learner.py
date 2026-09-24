import math
from typing import Dict, List


class HumanPreferenceLearner:
    def __init__(self, learning_rate: float = 0.1, exploration_rate: float = 0.05):
        self.learning_rate = max(0.0, min(1.0, learning_rate))
        self.exploration_rate = max(0.0, min(1.0, exploration_rate))
        self.preferences: Dict[str, float] = {}
        self.feedback_history: List[dict] = []
        self.confidence: Dict[str, float] = {}

    def register_option(self, option: str, initial_score: float = 0.5) -> None:
        self.preferences[option] = max(0.0, min(1.0, initial_score))
        self.confidence[option] = 0.5

    def learn_from_feedback(self, option: str, human_score: float) -> float:
        if option not in self.preferences:
            self.register_option(option)
        human_score = max(0.0, min(1.0, human_score))
        old = self.preferences[option]
        self.preferences[option] = old * (1.0 - self.learning_rate) + human_score * self.learning_rate
        self.confidence[option] = min(1.0, self.confidence.get(option, 0.5) + self.learning_rate)
        self.feedback_history.append({
            "option": option,
            "human_score": human_score,
            "previous_score": old,
            "new_score": self.preferences[option],
        })
        return self.preferences[option]

    def preference_ranking(self) -> List[str]:
        return sorted(self.preferences, key=lambda o: self.preferences.get(o, 0.0), reverse=True)

    def confidence_weighted_score(self, option: str) -> float:
        if option not in self.preferences:
            return 0.5
        return self.preferences[option] * self.confidence.get(option, 0.5)

    def exploration_choice(self) -> str:
        if not self.preferences:
            return ""
        import random
        if random.random() < self.exploration_rate:
            return max(self.preferences, key=self.preferences.get)
        return self.preference_ranking()[0]

    def average_feedback_quality(self) -> float:
        if not self.feedback_history:
            return 0.0
        return sum(abs(f["human_score"] - f["previous_score"]) for f in self.feedback_history) / len(self.feedback_history)
