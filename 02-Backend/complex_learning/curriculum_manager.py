from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Topic:
    name: str
    difficulty: float = 0.5
    dependencies: List[str] = field(default_factory=list)
    mastery: float = 0.0


class CurriculumManager:
    def __init__(self, mastery_threshold: float = 0.8, decay: float = 0.1):
        self.topics: Dict[str, Topic] = {}
        self.mastery_threshold = mastery_threshold
        self.decay = decay
        self.history: List[Dict] = []

    def add_topic(self, name: str, difficulty: float = 0.5, dependencies: Optional[List[str]] = None) -> None:
        deps = dependencies or []
        for dep in deps:
            if dep not in self.topics:
                raise ValueError(f"Dependency '{dep}' not registered")
        self.topics[name] = Topic(name=name, difficulty=difficulty, dependencies=deps)

    def update_mastery(self, name: str, score: float) -> None:
        if name not in self.topics:
            raise KeyError(f"Topic '{name}' not found")
        prev = self.topics[name].mastery
        self.topics[name].mastery = min(1.0, max(0.0, prev * (1 - self.decay) + score * self.decay))
        self.history.append({"topic": name, "prev_mastery": prev, "new_mastery": self.topics[name].mastery, "score": score})

    def _available(self) -> List[str]:
        ready = []
        for name, topic in self.topics.items():
            if topic.mastery >= self.mastery_threshold:
                continue
            if all(self.topics[d].mastery >= self.mastery_threshold for d in topic.dependencies):
                ready.append(name)
        return ready

    def schedule_next(self) -> Optional[str]:
        available = self._available()
        if not available:
            return None
        available.sort(key=lambda n: (self.topics[n].difficulty, n))
        return available[0]

    def get_progress(self) -> float:
        if not self.topics:
            return 0.0
        return sum(t.mastery for t in self.topics.values()) / len(self.topics)

    def mastered(self) -> List[str]:
        return [n for n, t in self.topics.items() if t.mastery >= self.mastery_threshold]
