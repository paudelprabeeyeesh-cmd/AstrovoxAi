"""Predictive analytics for platform forecasting."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Forecast:
    metric_name: str
    predicted_value: float
    confidence: float
    horizon_seconds: int
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PredictiveAnalytics:
    def __init__(self) -> None:
        self._forecasts: List[Forecast] = []

    def forecast(self, metric_name: str, history: List[float], horizon_seconds: int = 3600) -> Forecast:
        if not history:
            predicted = 0.0
        else:
            predicted = sum(history[-5:]) / min(len(history), 5)
        forecast = Forecast(
            metric_name=metric_name,
            predicted_value=predicted,
            confidence=0.8,
            horizon_seconds=horizon_seconds,
        )
        self._forecasts.append(forecast)
        return forecast

    def get_forecasts(self) -> List[Forecast]:
        return list(self._forecasts)


predictive_analytics = PredictiveAnalytics()
