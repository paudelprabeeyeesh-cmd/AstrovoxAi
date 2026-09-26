"""AI energy optimizer."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIOptimizationSuggestion:
    resource_id: str
    current_power_w: float
    suggested_power_w: float
    savings_percent: float
    reason: str


class AIEnergyOptimizer:
    def __init__(self) -> None:
        self._suggestions: List[AIOptimizationSuggestion] = []

    def analyze(self, resource_id: str, power_w: float, utilization: float) -> AIOptimizationSuggestion:
        suggested = power_w * max(0.5, utilization)
        savings = (power_w - suggested) / power_w * 100 if power_w > 0 else 0.0
        suggestion = AIOptimizationSuggestion(
            resource_id=resource_id,
            current_power_w=power_w,
            suggested_power_w=suggested,
            savings_percent=savings,
            reason="reduce idle power consumption",
        )
        self._suggestions.append(suggestion)
        return suggestion


ai_energy_optimizer = AIEnergyOptimizer()
