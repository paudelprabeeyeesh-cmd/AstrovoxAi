from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Demonstration:
    source_id: str
    task: str
    action: str
    outcome: float
    features: np.ndarray = field(default_factory=lambda: np.array([]))


class SocialLearning:
    def __init__(self, imitation_rate: float = 0.3, observation_window: int = 50):
        self.imitation_rate = imitation_rate
        self.observation_window = observation_window
        self.teachers: Dict[str, List[Dict[str, Any]]] = {}
        self.repertoire: Dict[str, Dict[str, float]] = {}
        self.demonstrations: List[Demonstration] = []
        self._counter = 0

    def observe(self, source_id: str, task: str, action: str, outcome: float, features: Optional[np.ndarray] = None) -> None:
        demo = Demonstration(
            source_id=source_id,
            task=task,
            action=action,
            outcome=max(0.0, min(1.0, outcome)),
            features=np.array(features) if features is not None else np.array([]),
        )
        self.demonstrations.append(demo)
        if source_id not in self.teachers:
            self.teachers[source_id] = []
        self.teachers[source_id].append({
            "task": task,
            "action": action,
            "outcome": demo.outcome,
        })
        if len(self.demonstrations) > 1000:
            self.demonstrations.pop(0)
        for key, val_list in self.teachers.items():
            if len(val_list) > self.observation_window:
                self.teachers[key] = val_list[-self.observation_window:]

    def imitate_best(self, task: str) -> Optional[str]:
        candidates = [d for d in self.demonstrations if d.task == task]
        if not candidates:
            return None
        best = max(candidates, key=lambda d: d.outcome)
        if np.random.random() < self.imitation_rate:
            return best.action
        return None

    def learn_from_peer(self, peer_id: str) -> Dict[str, float]:
        peer_demos = self.teachers.get(peer_id, [])
        action_scores: Dict[str, List[float]] = {}
        for demo in peer_demos:
            action_scores.setdefault(demo["action"], []).append(demo["outcome"])
        learned = {}
        for action, scores in action_scores.items():
            learned[action] = float(np.mean(scores))
        self.repertoire[peer_id] = learned
        return learned

    def get_imitation_candidates(self, task: str, top_k: int = 3) -> List[Dict[str, Any]]:
        candidates = [d for d in self.demonstrations if d.task == task]
        candidates.sort(key=lambda d: d.outcome, reverse=True)
        return candidates[:top_k]

    def social_repertoire_summary(self) -> Dict[str, Any]:
        return {
            "total_demonstrations": len(self.demonstrations),
            "peers": list(self.teachers.keys()),
            "repertoire_entries": len(self.repertoire),
            "imitation_rate": self.imitation_rate,
        }
