from dataclasses import dataclass, field
from typing import List, Optional
import random
import string


@dataclass
class Idea:
    content: str
    domain: str = "general"
    novelty: float = 0.0
    utility: float = 0.0
    feasibility: float = 0.0


class IdeaGenerator:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self.history: List[str] = []

    def generate(self, prompt: str, n: int = 3, domain: str = "general") -> List[Idea]:
        ideas = []
        tokens = prompt.lower().split()
        for i in range(n):
            variation = self._mutate(prompt, tokens, i)
            idea = Idea(content=variation, domain=domain)
            idea.novelty = self._novelty(variation)
            idea.utility = self._utility(variation, prompt)
            idea.feasibility = self._feasibility(variation)
            ideas.append(idea)
        ideas.sort(key=lambda x: x.novelty + x.utility + x.feasibility, reverse=True)
        return ideas

    def _mutate(self, prompt: str, tokens: List[str], index: int) -> str:
        if not tokens:
            return prompt
        adjectives = ["novel", "rapid", "scalable", "adaptive", "modular", "resilient", "intuitive", "hybrid"]
        verbs = ["reimagine", "orchestrate", "synthesize", "streamline", "augment", "blend", "restructure"]
        nouns = ["framework", "pipeline", "ecosystem", "paradigm", "workflow", "interface", "protocol"]
        random.shuffle(adjectives)
        random.shuffle(verbs)
        random.shuffle(nouns)
        seed = (index * 7 + len(prompt)) % 10
        parts = [prompt]
        if seed < 4:
            parts.append(f"by {verbs[seed % len(verbs)]} {nouns[seed % len(nouns)]}")
        elif seed < 7:
            parts.append(f"using {adjectives[seed % len(adjectives)]} {nouns[seed % len(nouns)]}")
        else:
            parts.append(f"through {adjectives[seed % len(adjectives)]} {verbs[seed % len(verbs)]}")
        return " ".join(parts)

    def _novelty(self, content: str) -> float:
        if not self.history:
            return 0.75
        words = set(content.lower().split())
        overlaps = [len(words & set(h.lower().split())) / max(len(words), 1) for h in self.history]
        novelty = 1.0 - (sum(overlaps) / len(overlaps))
        self.history.append(content)
        if len(self.history) > 100:
            self.history.pop(0)
        return max(0.0, min(1.0, novelty))

    def _utility(self, content: str, prompt: str) -> float:
        prompt_words = set(prompt.lower().split())
        content_words = set(content.lower().split())
        if not prompt_words:
            return 0.5
        overlap = len(prompt_words & content_words) / len(prompt_words)
        length = len(content.split())
        length_score = 1.0 if 5 <= length <= 60 else 0.5
        return max(0.0, min(1.0, 0.6 * overlap + 0.4 * length_score))

    def _feasibility(self, content: str) -> float:
        words = content.lower().split()
        unique_ratio = len(set(words)) / max(len(words), 1)
        length_score = 1.0 if 3 <= len(words) <= 40 else 0.6
        return max(0.0, min(1.0, 0.5 * unique_ratio + 0.5 * length_score))
