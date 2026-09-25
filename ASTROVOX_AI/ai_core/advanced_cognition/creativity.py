from dataclasses import dataclass, field
from typing import Any
import time
import random


@dataclass
class CreativityMetric:
    fluency: float
    originality: float
    flexibility: float
    elaboration: float
    synthesis_score: float = 0.0
    divergent_thinking: float = 0.0
    convergent_thinking: float = 0.0
    aesthetic_quality: float = 0.0
    utility_score: float = 0.0
    timestamp: float = field(default_factory=time.time)


class CreativityMetrics:
    def __init__(self):
        self.history: list[CreativityMetric] = []
        self.baseline: dict[str, float] = {
            "fluency": 0.5,
            "originality": 0.5,
            "flexibility": 0.5,
            "elaboration": 0.5,
            "synthesis_score": 0.4,
            "divergent_thinking": 0.5,
            "convergent_thinking": 0.5,
            "aesthetic_quality": 0.4,
            "utility_score": 0.5,
        }
        self.enhancement_log: list[dict[str, Any]] = []
        self.domain_vocabularies: dict[str, list[str]] = {}

    def evaluate(self, ideas: list[str], domain: str | None = None) -> CreativityMetric:
        if not ideas:
            return CreativityMetric(fluency=0.0, originality=0.0, flexibility=0.0, elaboration=0.0)
        fluency = min(1.0, len(ideas) / 10.0)
        unique = len(set(ideas))
        originality = unique / max(len(ideas), 1)
        word_lengths = [len(idea.split()) for idea in ideas]
        categories = len(set(word_lengths))
        flexibility = min(1.0, categories / 5.0)
        avg_len = sum(len(idea) for idea in ideas) / len(ideas)
        elaboration = min(1.0, avg_len / 15.0)
        synthesis = self._score_synthesis(ideas)
        divergent = self._score_divergent(ideas)
        convergent = self._score_convergent(ideas)
        aesthetic = self._score_aesthetic(ideas)
        utility = self._score_utility(ideas, domain)
        metric = CreativityMetric(
            fluency=fluency,
            originality=originality,
            flexibility=flexibility,
            elaboration=elaboration,
            synthesis_score=synthesis,
            divergent_thinking=divergent,
            convergent_thinking=convergent,
            aesthetic_quality=aesthetic,
            utility_score=utility,
        )
        self.history.append(metric)
        return metric

    def enhance(self, metric: CreativityMetric, strategy: str = "balanced") -> CreativityMetric:
        factors = {
            "balanced": (1.1, 1.15, 1.1, 1.1, 1.12, 1.08, 1.08, 1.1, 1.08),
            "divergent": (1.05, 1.2, 1.15, 1.05, 1.1, 1.25, 1.0, 1.05, 1.0),
            "convergent": (1.15, 1.05, 1.05, 1.15, 1.05, 1.0, 1.2, 1.1, 1.15),
            "aesthetic": (1.05, 1.1, 1.05, 1.2, 1.1, 1.05, 1.05, 1.25, 1.0),
            "synthesis": (1.1, 1.15, 1.1, 1.1, 1.25, 1.1, 1.1, 1.05, 1.1),
        }
        f = factors.get(strategy, factors["balanced"])
        enhanced = CreativityMetric(
            fluency=min(1.0, metric.fluency * f[0]),
            originality=min(1.0, metric.originality * f[1]),
            flexibility=min(1.0, metric.flexibility * f[2]),
            elaboration=min(1.0, metric.elaboration * f[3]),
            synthesis_score=min(1.0, metric.synthesis_score * f[4]),
            divergent_thinking=min(1.0, metric.divergent_thinking * f[5]),
            convergent_thinking=min(1.0, metric.convergent_thinking * f[6]),
            aesthetic_quality=min(1.0, metric.aesthetic_quality * f[7]),
            utility_score=min(1.0, metric.utility_score * f[8]),
        )
        self.enhancement_log.append({
            "timestamp": time.time(),
            "strategy": strategy,
            "before": metric.__dict__,
            "after": enhanced.__dict__,
        })
        return enhanced

    def register_domain_vocabulary(self, domain: str, terms: list[str]):
        self.domain_vocabularies[domain] = terms

    def get_creativity_report(self) -> dict[str, Any]:
        if not self.history:
            return {"status": "no_data"}
        latest = self.history[-1]
        return {
            "total_evaluations": len(self.history),
            "latest_metric": {
                "fluency": round(latest.fluency, 4),
                "originality": round(latest.originality, 4),
                "flexibility": round(latest.flexibility, 4),
                "elaboration": round(latest.elaboration, 4),
                "synthesis": round(latest.synthesis_score, 4),
                "divergent": round(latest.divergent_thinking, 4),
                "convergent": round(latest.convergent_thinking, 4),
                "aesthetic": round(latest.aesthetic_quality, 4),
                "utility": round(latest.utility_score, 4),
            },
            "baseline_comparison": {
                k: round(v - self.baseline.get(k, 0.5), 4) for k, v in latest.__dict__.items() if k != "timestamp"
            },
            "enhancements_applied": len(self.enhancement_log),
        }

    def _score_synthesis(self, ideas: list[str]) -> float:
        if len(ideas) < 2:
            return 0.0
        pairs = [(ideas[i], ideas[j]) for i in range(len(ideas)) for j in range(i + 1, len(ideas))]
        combined_scores = [len(set(a.split()) & set(b.split())) / max(len(set(a.split()) | set(b.split())), 1) for a, b in pairs]
        return min(1.0, 0.3 + 0.5 * (sum(combined_scores) / max(len(combined_scores), 1)))

    def _score_divergent(self, ideas: list[str]) -> float:
        unique_starts = len(set(idea.split()[0] for idea in ideas if idea.split()))
        return min(1.0, 0.2 + 0.6 * unique_starts / max(len(ideas), 1))

    def _score_convergent(self, ideas: list[str]) -> float:
        if not ideas:
            return 0.0
        word_freq: dict[str, int] = {}
        for idea in ideas:
            for word in idea.split():
                word_freq[word] = word_freq.get(word, 0) + 1
        common = sum(1 for count in word_freq.values() if count > 1)
        return min(1.0, 0.2 + 0.5 * common / max(len(word_freq), 1))

    def _score_aesthetic(self, ideas: list[str]) -> float:
        if not ideas:
            return 0.0
        avg_len = sum(len(idea) for idea in ideas) / len(ideas)
        return min(1.0, 0.3 + 0.4 * (avg_len / 30.0) + 0.2 * random.random())

    def _score_utility(self, ideas: list[str], domain: str | None) -> float:
        if not ideas:
            return 0.0
        domain_terms = set(self.domain_vocabularies.get(domain or "", []))
        if not domain_terms:
            return 0.5
        coverage = sum(len(set(idea.split()) & domain_terms) for idea in ideas) / max(sum(len(idea.split()) for idea in ideas), 1)
        return min(1.0, 0.3 + 0.5 * coverage)
