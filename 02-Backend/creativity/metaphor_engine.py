from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random


@dataclass
class Metaphor:
    source: str
    target: str
    text: str
    strength: float = 0.0
    clarity: float = 0.0


class MetaphorEngine:
    def __init__(self, seed: Optional[int] = None):
        self._rand = random.Random(seed)
        self.domains = {
            "nature": ["river", "mountain", "forest", "storm", "seed", "ocean", "wind", "fire"],
            "technology": ["circuit", "algorithm", "network", "engine", "pipeline", "database", "protocol"],
            "human": ["heart", "mind", "voice", "hand", "eye", "blood", "breath", "shadow"],
            "time": ["clock", "river", "season", "tide", "dawn", "twilight", "cycle", "march"],
        }
        self.templates = [
            "the {target} is a {source}",
            "like a {source}, the {target}",
            "the {target} flows as a {source}",
            "a {source} of {target}",
            "the {target} wears the mask of a {source}",
        ]

    def generate(self, target: str, source_domain: Optional[str] = None, n: int = 3) -> List[Metaphor]:
        if source_domain and source_domain in self.domains:
            sources = list(self.domains[source_domain])
        else:
            sources = [item for items in self.domains.values() for item in items]
        metaphors = []
        self._rand.shuffle(sources)
        for i in range(min(n, len(sources))):
            source = sources[i]
            text = self._compose(target, source)
            strength = self._strength(target, source)
            clarity = self._clarity(text)
            metaphors.append(Metaphor(source=source, target=target, text=text, strength=strength, clarity=clarity))
        metaphors.sort(key=lambda m: m.strength + m.clarity, reverse=True)
        return metaphors

    def _compose(self, target: str, source: str) -> str:
        template = self._rand.choice(self.templates)
        return template.format(target=target, source=source)

    def _strength(self, target: str, source: str) -> float:
        t_chars = set(target.lower())
        s_chars = set(source.lower())
        overlap = len(t_chars & s_chars) / max(len(t_chars | s_chars), 1)
        length_factor = 1.0 if 3 <= len(target) <= 20 and 3 <= len(source) <= 20 else 0.7
        return max(0.0, min(1.0, 0.5 * overlap + 0.5 * length_factor))

    def _clarity(self, text: str) -> float:
        words = text.lower().split()
        unique = len(set(words))
        total = len(words)
        richness = unique / max(total, 1)
        length_score = 1.0 if 3 <= total <= 12 else 0.6
        return max(0.0, min(1.0, 0.6 * richness + 0.4 * length_score))

    def map_domain(self, target: str, domain: str, n: int = 3) -> List[Metaphor]:
        return self.generate(target=target, source_domain=domain, n=n)
