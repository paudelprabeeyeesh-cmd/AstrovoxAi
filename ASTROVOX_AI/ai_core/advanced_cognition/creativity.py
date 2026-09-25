from dataclasses import dataclass, field
from typing import Any


@dataclass
class CreativityMetric:
    fluency: float
    originality: float
    flexibility: float
    elaboration: float
    timestamp: float


class CreativityMetrics:
    def __init__(self):
        self.history: list[CreativityMetric] = []
        self.baseline: dict[str, float] = {
            "fluency": 0.5,
            "originality": 0.5,
            "flexibility": 0.5,
            "elaboration": 0.5,
        }

    def evaluate(self, ideas: list[str]) -> CreativityMetric:
        fluency = min(1.0, len(ideas) / 10.0)
        unique = len(set(ideas))
        originality = unique / max(len(ideas), 1)
        categories = len(set(len(idea.split()) for idea in ideas))
        flexibility = min(1.0, categories / 5.0)
        elaboration = sum(len(idea) for idea in ideas) / max(len(ideas) * 10, 1)
        elaboration = min(1.0, elaboration)
        metric = CreativityMetric(
            fluency=fluency,
            originality=originality,
            flexibility=flexibility,
            elaboration=elaboration,
            timestamp=__import__("time").time(),
        )
        self.history.append(metric)
        return metric

    def enhance(self, metric: CreativityMetric) -> CreativityMetric:
        return CreativityMetric(
            fluency=min(1.0, metric.fluency * 1.1),
            originality=min(1.0, metric.originality * 1.15),
            flexibility=min(1.0, metric.flexibility * 1.1),
            elaboration=min(1.0, metric.elaboration * 1.1),
            timestamp=__import__("time").time(),
        )
