from typing import Any, Dict, List, Optional, Tuple


class AbductiveReasoner:
    def __init__(self):
        self._hypotheses: List[Dict[str, Any]] = []
        self._observations: List[str] = []

    def add_observation(self, observation: str) -> None:
        self._observations.append(observation)

    def add_hypothesis(self, hypothesis: str, explanation_for: str, likelihood: float) -> None:
        self._hypotheses.append({
            "hypothesis": hypothesis,
            "explains": explanation_for,
            "likelihood": likelihood,
        })

    def explain(self, observation: str) -> List[Tuple[str, float]]:
        candidates = []
        for h in self._hypotheses:
            if h["explains"] == observation:
                candidates.append((h["hypothesis"], h["likelihood"]))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def best_explanation(self, observation: str) -> Optional[str]:
        candidates = self.explain(observation)
        if candidates:
            return candidates[0][0]
        return None
