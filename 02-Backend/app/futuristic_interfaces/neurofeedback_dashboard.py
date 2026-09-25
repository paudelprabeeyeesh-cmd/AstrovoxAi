import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class NeurofeedbackMetric:
    metric_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    metric: str = "alpha_power"
    value: float = 0.0
    target_range: tuple[float, float] = (0.0, 1.0)
    unit: str = ""
    electrode: Optional[str] = None
    quality: str = "good"
    timestamp: float = field(default_factory=time.time)


@dataclass
class NeurofeedbackSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    target_band: str = "alpha"
    target_value: float = 0.5
    duration_seconds: int = 300
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    score: float = 0.0
    metrics: list[NeurofeedbackMetric] = field(default_factory=list)


class NeurofeedbackDashboard:
    def __init__(self) -> None:
        self.sessions: dict[str, NeurofeedbackSession] = {}
        self.metrics: dict[str, list[NeurofeedbackMetric]] = {}

    def start_session(self, user_id: str, target_band: str, target_value: float, duration_seconds: int = 300) -> dict[str, Any]:
        session = NeurofeedbackSession(
            user_id=user_id,
            target_band=target_band,
            target_value=target_value,
            duration_seconds=duration_seconds,
        )
        self.sessions[session.session_id] = session
        self.metrics[session.session_id] = []
        logger.info("Neurofeedback session started: session_id=%s target=%s", session.session_id, target_band)
        return {
            "session_id": session.session_id,
            "user_id": user_id,
            "target_band": target_band,
            "target_value": target_value,
            "duration_seconds": duration_seconds,
            "started_at": session.started_at,
        }

    def end_session(self, session_id: str) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"session_id": session_id, "status": "not_found"}
        session.ended_at = time.time()
        session.score = self._compute_score(session_id)
        return {
            "session_id": session_id,
            "status": "ended",
            "score": session.score,
            "duration_seconds": session.duration_seconds,
            "metrics_collected": len(self.metrics.get(session_id, [])),
        }

    def record_metric(self, session_id: str, metric: str, value: float, unit: str, electrode: Optional[str] = None) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"status": "error", "error": "Session not found"}
        target_range = (0.0, 1.0)
        if metric == "alpha_power":
            target_range = (0.2, 0.5)
        elif metric == "beta_power":
            target_range = (0.1, 0.3)
        elif metric == "theta_power":
            target_range = (0.15, 0.4)
        elif metric == "delta_power":
            target_range = (0.3, 0.6)
        elif metric == "gamma_power":
            target_range = (0.05, 0.2)

        m = NeurofeedbackMetric(
            session_id=session_id,
            metric=metric,
            value=value,
            target_range=target_range,
            unit=unit,
            electrode=electrode,
        )
        self.metrics.setdefault(session_id, []).append(m)
        return {
            "status": "recorded",
            "metric_id": m.metric_id,
            "in_target_range": target_range[0] <= value <= target_range[1],
        }

    def get_dashboard(self, session_id: str) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"session_id": session_id, "status": "not_found"}
        session_metrics = self.metrics.get(session_id, [])
        latest = session_metrics[-10:] if session_metrics else []
        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "target_band": session.target_band,
            "target_value": session.target_value,
            "score": session.score,
            "active": session.ended_at is None,
            "latest_metrics": [
                {
                    "metric": m.metric,
                    "value": m.value,
                    "unit": m.unit,
                    "electrode": m.electrode,
                    "in_target": m.target_range[0] <= m.value <= m.target_range[1],
                    "timestamp": m.timestamp,
                }
                for m in latest
            ],
            "total_metrics": len(session_metrics),
        }

    def _compute_score(self, session_id: str) -> float:
        session_metrics = self.metrics.get(session_id, [])
        if not session_metrics:
            return 0.0
        target_band = self.sessions.get(session_id)
        if not target_band:
            return 0.0
        target = target_band.target_value
        in_target = sum(1 for m in session_metrics if m.target_range[0] <= m.value <= m.target_range[1])
        return round(in_target / len(session_metrics), 3)
