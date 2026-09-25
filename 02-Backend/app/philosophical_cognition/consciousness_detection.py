from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ConsciousnessIndicator(str, Enum):
    INTEGRATED_INFORMATION = "integrated_information"
    GLOBAL_WORKSPACE = "global_workspace"
    SELF_MODEL = "self_model"
    REPORTABILITY = "reportability"
    PHENOMENAL_BINDING = "phenomenal_binding"
    TEMPORAL_INTEGRATION = "temporal_integration"


@dataclass
class ConsciousnessSignature:
    indicators: Dict[ConsciousnessIndicator, float]
    integrated_score: float = 0.0
    confidence: float = 0.0
    explanation: str = ""

    def __post_init__(self) -> None:
        if not self.integrated_score and self.indicators:
            self.integrated_score = sum(self.indicators.values()) / len(self.indicators)
        if not self.confidence:
            self.confidence = self.integrated_score


class ConsciousnessDetectionTests:
    def __init__(self) -> None:
        self.indicator_thresholds = {
            ConsciousnessIndicator.INTEGRATED_INFORMATION: 0.7,
            ConsciousnessIndicator.GLOBAL_WORKSPACE: 0.75,
            ConsciousnessIndicator.SELF_MODEL: 0.65,
            ConsciousnessIndicator.REPORTABILITY: 0.6,
            ConsciousnessIndicator.PHENOMENAL_BINDING: 0.7,
            ConsciousnessIndicator.TEMPORAL_INTEGRATION: 0.6,
        }

    def test_integrated_information(self, phi: float) -> float:
        return max(0.0, min(1.0, phi))

    def test_global_workspace(self, accessibility: float, broadcast_power: float) -> float:
        return max(0.0, min(1.0, (accessibility + broadcast_power) / 2))

    def test_self_model(self, self_representation_accuracy: float) -> float:
        return max(0.0, min(1.0, self_representation_accuracy))

    def evaluate(self, measurements: Dict[ConsciousnessIndicator, float]) -> ConsciousnessSignature:
        indicators = {k: max(0.0, min(1.0, v)) for k, v in measurements.items()}
        signature = ConsciousnessSignature(indicators=indicators)
        failed = [k.value for k, v in indicators.items() if v < self.indicator_thresholds.get(k, 0.5)]
        if failed:
            signature.explanation = f"Below threshold on: {', '.join(failed)}"
        else:
            signature.explanation = "All consciousness indicators above threshold"
        return signature
