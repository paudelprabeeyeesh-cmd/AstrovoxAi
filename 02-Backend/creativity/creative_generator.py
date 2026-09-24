from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class CreativeOutput:
    content: str
    novelty: float
    utility: float
    surprise: float
    combined_score: float = 0.0


class CreativeGenerator:
    def __init__(self, temperature: float = 0.8, novelty_weight: float = 0.4, utility_weight: float = 0.4, surprise_weight: float = 0.2):
        self.temperature = temperature
        self.novelty_weight = novelty_weight
        self.utility_weight = utility_weight
        self.surprise_weight = surprise_weight
        self.history: List[str] = []

    def generate(self, prompt: str, n: int = 3, domain_context: Optional[List[str]] = None) -> List[CreativeOutput]:
        outputs = self._diverge(prompt, n, domain_context)
        scored = [self._score(o, prompt) for o in outputs]
        return sorted(scored, key=lambda x: x.combined_score, reverse=True)

    def _diverge(self, prompt: str, n: int, context: Optional[List[str]]) -> List[str]:
        base = self._associate(prompt)
        variations = []
        for i in range(n):
            noise = np.random.normal(0, self.temperature * 0.1, len(base))
            varied = base + noise
            varied = np.clip(varied, 0.0, 1.0)
            text = self._decode(prompt, varied, context)
            variations.append(text)
        return variations

    def _associate(self, prompt: str) -> np.ndarray:
        tokens = prompt.lower().split()
        vec = np.zeros(128)
        for i, token in enumerate(tokens):
            idx = hash(token) % 128
            vec[idx] += 1.0 / (i + 1)
        return vec / max(np.linalg.norm(vec), 1e-6)

    def _decode(self, prompt: str, vector: np.ndarray, context: Optional[List[str]]) -> str:
        parts = [prompt]
        if context:
            parts.append("based on: " + ", ".join(context[:3]))
        parts.append(f"idea_{np.argmax(vector)}")
        return " ".join(parts)

    def _score(self, content: str, prompt: str) -> CreativeOutput:
        novelty = self._compute_novelty(content)
        utility = self._compute_utility(content, prompt)
        surprise = self._compute_surprise(content)
        combined = (
            self.novelty_weight * novelty
            + self.utility_weight * utility
            + self.surprise_weight * surprise
        )
        return CreativeOutput(
            content=content, novelty=novelty, utility=utility, surprise=surprise, combined_score=combined
        )

    def _compute_novelty(self, content: str) -> float:
        if not self.history:
            return 0.8
        tokens = set(content.lower().split())
        overlaps = [len(tokens & set(h.lower().split())) / max(len(tokens), 1) for h in self.history]
        novelty = 1.0 - np.mean(overlaps) if overlaps else 0.8
        self.history.append(content)
        if len(self.history) > 100:
            self.history.pop(0)
        return max(0.0, min(1.0, novelty))

    def _compute_utility(self, content: str, prompt: str) -> float:
        prompt_words = set(prompt.lower().split())
        content_words = set(content.lower().split())
        if not prompt_words:
            return 0.5
        overlap = len(prompt_words & content_words) / len(prompt_words)
        length = len(content.split())
        length_score = 1.0 if 10 <= length <= 100 else 0.6
        return max(0.0, min(1.0, 0.5 * overlap + 0.5 * length_score))

    def _compute_surprise(self, content: str) -> float:
        words = content.split()
        if len(words) < 2:
            return 0.0
        transitions = [words[i] + "_" + words[i + 1] for i in range(len(words) - 1)]
        unique_ratio = len(set(transitions)) / len(transitions)
        return min(1.0, unique_ratio * 0.8 + 0.2)

    def combine_outputs(self, outputs: List[CreativeOutput], strategy: str = "pareto") -> CreativeOutput:
        if not outputs:
            return CreativeOutput(content="", novelty=0.0, utility=0.0, surprise=0.0)
        if strategy == "max_novelty":
            best = max(outputs, key=lambda x: x.novelty)
        elif strategy == "max_utility":
            best = max(outputs, key=lambda x: x.utility)
        elif strategy == "pareto":
            best = max(outputs, key=lambda x: x.combined_score)
        else:
            best = outputs[0]
        return best
