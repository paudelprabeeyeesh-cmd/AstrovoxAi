"""Time series forecasting model."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesPoint:
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Forecast:
    forecast_id: str
    horizon: int
    predictions: List[float]
    confidence_intervals: List[Tuple[float, float]]
    model_version: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ForecastingModel:
    def __init__(self, model_version: str = "v1") -> None:
        self._series: Dict[str, List[TimeSeriesPoint]] = {}
        self._model_version = model_version

    def add_series(self, series_id: str, points: List[TimeSeriesPoint]) -> None:
        self._series[series_id] = sorted(points, key=lambda p: p.timestamp)

    def forecast(self, series_id: str, horizon: int = 10) -> Forecast:
        series = self._series.get(series_id)
        if not series:
            raise ValueError(f"Unknown series: {series_id}")
        values = [p.value for p in series]
        predictions = self._ses_forecast(values, horizon)
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        confidence_intervals = [(p - 1.96 * math.sqrt(variance), p + 1.96 * math.sqrt(variance)) for p in predictions]
        return Forecast(
            forecast_id=str(__import__("uuid").uuid4()),
            horizon=horizon,
            predictions=predictions,
            confidence_intervals=confidence_intervals,
            model_version=self._model_version,
        )

    @staticmethod
    def _ses_forecast(values: List[float], horizon: int, alpha: float = 0.3) -> List[float]:
        if not values:
            return [0.0] * horizon
        level = values[0]
        for v in values[1:]:
            level = alpha * v + (1 - alpha) * level
        return [level] * horizon

    def detect_anomalies(self, series_id: str, threshold: float = 2.0) -> List[Dict[str, Any]]:
        series = self._series.get(series_id, [])
        if len(series) < 2:
            return []
        values = [p.value for p in series]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance else 0.0
        anomalies = []
        for point in series:
            if std > 0 and abs(point.value - mean) > threshold * std:
                anomalies.append({
                    "timestamp": point.timestamp.isoformat(),
                    "value": point.value,
                    "z_score": (point.value - mean) / std,
                })
        return anomalies


forecasting_model = ForecastingModel()
