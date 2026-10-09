from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class Idea:
    content: str
    domain: str
    novelty: float
    utility: float
    feasibility: float = 0.5


class CreativeIntelligence:
    def __init__(self, temperature: float = 0.8):
        self.temperature = temperature
        self.history: List[Idea] = []

    def generate_ideas(self, problem: str, domain: str, n: int = 3) -> List[Idea]:
        ideas = []
        for i in range(n):
            novelty = min(1.0, max(0.0, np.random.normal(0.6, self.temperature * 0.1)))
            utility = min(1.0, max(0.0, np.random.normal(0.5, self.temperature * 0.1)))
            content = f"{problem}: idea_{i}_{domain}"
            ideas.append(Idea(content=content, domain=domain, novelty=novelty, utility=utility, feasibility=0.5))
        self.history.extend(ideas)
        return ideas

    def evaluate(self, idea: Idea) -> float:
        return float(np.mean([idea.novelty, idea.utility, idea.feasibility]))

    def combine(self, ideas: List[Idea]) -> Optional[Idea]:
        if not ideas:
            return None
        novelty = float(np.mean([i.novelty for i in ideas]))
        utility = float(np.max([i.utility for i in ideas]))
        feasibility = float(np.mean([i.feasibility for i in ideas]))
        combined_content = " ".join([i.content for i in ideas])
        return Idea(content=combined_content, domain=ideas[0].domain, novelty=novelty, utility=utility, feasibility=feasibility)

    def get_best_idea(self, ideas: List[Idea]) -> Optional[Idea]:
        if not ideas:
            return None
        scored = [(self.evaluate(i), i) for i in ideas]
        return max(scored, key=lambda x: x[0])[1]
