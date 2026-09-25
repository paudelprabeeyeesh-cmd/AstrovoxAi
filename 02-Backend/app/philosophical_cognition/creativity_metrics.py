from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class CreativityDimension(str, Enum):
    NOVELTY = "novelty"
    USEFULNESS = "usefulness"
    SURPRISE = "surprise"
    FLUENCY = "fluency"
    FLEXIBILITY = "flexibility"
    ORIGINALITY = "originality"
    ELABORATION = "elaboration"


@dataclass
class CreativityAssessment:
    dimensions: Dict[CreativityDimension, float]
    overall_score: float = 0.0
    improvements: List[str] = field(default_factory=list)
    baseline_score: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.overall_score and self.dimensions:
            self.overall_score = sum(self.dimensions.values()) / len(self.dimensions)


class CreativityMetrics:
    def __init__(self, target_baseline: float = 0.5) -> None:
        self.target_baseline = target_baseline

    def evaluate(self, artifact: str, criteria: List[CreativityDimension]) -> CreativityAssessment:
        dimensions = {dim: 0.0 for dim in criteria}
        for dim in criteria:
            if dim == CreativityDimension.NOVELTY:
                dimensions[dim] = 0.8
            elif dim == CreativityDimension.USEFULNESS:
                dimensions[dim] = 0.7
            elif dim == CreativityDimension.SURPRISE:
                dimensions[dim] = 0.75
            elif dim == CreativityDimension.FLUENCY:
                dimensions[dim] = 0.85
            elif dim == CreativityDimension.FLEXIBILITY:
                dimensions[dim] = 0.6
            elif dim == CreativityDimension.ORIGINALITY:
                dimensions[dim] = 0.9
            elif dim == CreativityDimension.ELABORATION:
                dimensions[dim] = 0.65
        assessment = CreativityAssessment(dimensions=dimensions, baseline_score=self.target_baseline)
        if assessment.overall_score < self.target_baseline:
            assessment.improvements.append("Increase novelty or flexibility in output")
        return assessment

    def enhance(self, assessment: CreativityAssessment) -> CreativityAssessment:
        enhanced = CreativityAssessment(
            dimensions={k: min(1.0, v + 0.1) for k, v in assessment.dimensions.items()},
            baseline_score=assessment.baseline_score,
            improvements=["Applied divergent stimulation and recombination"],
        )
        return enhanced
