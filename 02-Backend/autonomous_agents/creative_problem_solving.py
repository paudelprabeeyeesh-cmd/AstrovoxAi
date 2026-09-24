from typing import List, Dict, Optional, Tuple
import numpy as np


class CreativeProblemSolving:
    def __init__(self, divergence_factor: float = 0.8, convergence_patience: int = 3):
        self.divergence_factor = divergence_factor
        self.convergence_patience = convergence_patience
        self.solution_space: List[Dict[str, Any]] = []

    def divergent_thinking(self, problem: str, n_ideas: int = 5) -> List[Dict[str, Any]]:
        ideas = []
        for i in range(n_ideas):
            angle = (2.0 * np.pi * i) / n_ideas
            variation = self._variate(problem, angle)
            ideas.append({
                "id": f"idea_{i}",
                "content": variation,
                "angle": angle,
                "originality": float(np.abs(np.sin(angle)) * self.divergence_factor),
            })
        return ideas

    def converge_solutions(self, ideas: List[Dict[str, Any]], iterations: int = 3) -> List[Dict[str, Any]]:
        current = list(ideas)
        for _ in range(iterations):
            scored = [self._score_idea(idea) for idea in current]
            scored.sort(key=lambda x: x["score"], reverse=True)
            top = scored[: max(1, len(scored) // 2)]
            current = []
            for idea in top:
                for j in range(2):
                    mutated = dict(idea)
                    mutated["content"] = self._mutate(idea["content"])
                    mutated["originality"] = max(0.0, min(1.0, idea["originality"] + np.random.normal(0, 0.05)))
                    current.append(mutated)
        return current

    def analogical_transfer(self, source_domain: str, target_problem: str) -> Dict[str, Any]:
        mapping = self._build_mapping(source_domain, target_problem)
        return {
            "source": source_domain,
            "target": target_problem,
            "mapping": mapping,
            "transferred_solution": f"{source_domain}:{target_problem}::{mapping}",
        }

    def get_innovation_score(self, solution: Dict[str, Any]) -> float:
        originality = solution.get("originality", 0.0)
        feasibility = solution.get("feasibility", 0.5)
        return max(0.0, min(1.0, 0.6 * originality + 0.4 * feasibility))

    def _variate(self, problem: str, angle: float) -> str:
        tokens = problem.split()
        offset = int(np.floor(np.abs(np.sin(angle)) * len(tokens))) % max(len(tokens), 1)
        rotated = tokens[offset:] + tokens[:offset]
        return " ".join(rotated) + f"_{int(angle * 180 / np.pi) % 360}"

    def _score_idea(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        score = idea.get("originality", 0.0) * 0.7 + np.random.uniform(0.0, 0.3) * 0.3
        idea["score"] = max(0.0, min(1.0, score))
        return idea

    def _mutate(self, content: str) -> str:
        words = content.split()
        if not words:
            return content
        idx = np.random.randint(0, len(words))
        prefix = words[idx][:3] if len(words[idx]) > 3 else words[idx]
        words[idx] = prefix + "_mut"
        return " ".join(words)

    def _build_mapping(self, source: str, target: str) -> str:
        src_chars = list(source)
        tgt_chars = list(target)
        pairs = []
        for i in range(min(4, len(src_chars), len(tgt_chars))):
            pairs.append(f"{src_chars[i]}->{tgt_chars[i]}")
        return ";".join(pairs)
