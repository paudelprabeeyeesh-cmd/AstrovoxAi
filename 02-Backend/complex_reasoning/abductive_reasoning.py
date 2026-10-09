import numpy as np
from typing import List, Tuple, Optional


class Hypothesis:
    def __init__(self, description: str, prior: float = 0.1, explanation_power: float = 0.0):
        self.description = description
        self.prior = prior
        self.explanation_power = explanation_power
        self.likelihood: float = 0.0
        self.posterior: float = 0.0

    def update_posterior(self, likelihood: float) -> float:
        self.likelihood = likelihood
        self.posterior = self.prior * self.likelihood
        return self.posterior


class AbductiveEngine:
    def __init__(self, hypotheses: Optional[List[Hypothesis]] = None):
        self.hypotheses = hypotheses or []
        self.observations: List[str] = []
        self.beam_width: int = 5

    def add_hypothesis(self, hypothesis: Hypothesis):
        self.hypotheses.append(hypothesis)

    def set_observations(self, observations: List[str]):
        self.observations = observations

    def _compute_likelihood(self, hypothesis: Hypothesis) -> float:
        if not self.observations:
            return hypothesis.likelihood if hypothesis.likelihood > 0 else 1.0
        matched = sum(1 for obs in self.observations if hypothesis.description.lower() in obs.lower())
        return matched / len(self.observations)

    def _compute_simplicity(self, hypothesis: Hypothesis) -> float:
        words = hypothesis.description.split()
        return 1.0 / max(len(words), 1)

    def generate_best(self, top_k: int = 3) -> List[Tuple[Hypothesis, float]]:
        results = []
        for h in self.hypotheses:
            h.prior = max(h.prior, 0.01)
            likelihood = self._compute_likelihood(h)
            h.likelihood = likelihood
            h.explanation_power = likelihood
            h.posterior = h.prior * likelihood
            prior_penalty = 1.0 + np.log(h.prior)
            prior_factor = h.prior * h.explanation_power
            results.append((h, h.posterior * prior_factor / max(prior_penalty, 0.1)))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def beam_search(self, depth: int = 3) -> List[Hypothesis]:
        if not self.hypotheses:
            return []
        beams = [(h, self._compute_likelihood(h)) for h in self.hypotheses[: self.beam_width]]
        for _ in range(depth - 1):
            expanded = []
            for h, score in beams:
                for nh in self.hypotheses:
                    combined_desc = h.description + " AND " + nh.description
                    new_h = Hypothesis(description=combined_desc, prior=h.prior * nh.prior * 0.5)
                    new_score = self._compute_likelihood(new_h) * score
                    expanded.append((new_h, new_score))
            expanded.sort(key=lambda x: x[1], reverse=True)
            beams = expanded[: self.beam_width]
        return [h for h, _ in beams]
