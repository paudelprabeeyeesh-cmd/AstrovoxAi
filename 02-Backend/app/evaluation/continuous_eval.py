import logging
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ContinuousEvaluator:
    def __init__(self, evaluation_fn: Callable[[], dict[str, Any]], interval_seconds: float = 3600.0):
        self.evaluation_fn = evaluation_fn
        self.interval_seconds = interval_seconds
        self._history: list[dict[str, Any]] = []
        self._running = False
        self._last_run: Optional[float] = None

    def start(self) -> None:
        self._running = True
        logger.info("Continuous evaluator started with interval %.2fs", self.interval_seconds)

    def stop(self) -> None:
        self._running = False
        logger.info("Continuous evaluator stopped")

    def run_once(self) -> dict[str, Any]:
        start = time.time()
        try:
            result = self.evaluation_fn()
            latency = time.time() - start
            record = {
                "timestamp": time.time(),
                "status": "passed",
                "latency_ms": round(latency * 1000, 2),
                "details": result,
            }
            self._history.append(record)
            self._last_run = time.time()
            logger.info("Continuous eval passed in %.2fms", record["latency_ms"])
            return record
        except Exception as exc:  # noqa: BLE001
            record = {
                "timestamp": time.time(),
                "status": "failed",
                "latency_ms": 0.0,
                "error": str(exc),
            }
            self._history.append(record)
            self._last_run = time.time()
            logger.error("Continuous eval failed: %s", exc)
            return record

    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def summary(self) -> dict[str, Any]:
        if not self._history:
            return {"count": 0, "pass_rate": 0.0}
        passed = sum(1 for h in self._history if h["status"] == "passed")
        avg_latency = sum(h["latency_ms"] for h in self._history if h["status"] == "passed") / max(passed, 1)
        return {
            "count": len(self._history),
            "passed": passed,
            "failed": len(self._history) - passed,
            "pass_rate": round(passed / len(self._history), 4),
            "avg_latency_ms": round(avg_latency, 2),
            "last_run": self._last_run,
        }

    def detect_regression(self, baseline_score: float, threshold: float = 0.05) -> Optional[dict[str, Any]]:
        if not self._history:
            return None
        latest = self._history[-1]
        if latest["status"] == "failed":
            return {"regression": True, "reason": "latest_run_failed"}
        details = latest.get("details", {})
        current_score = details.get("overall", details.get("score", 1.0))
        if isinstance(current_score, (int, float)) and current_score < baseline_score - threshold:
            return {
                "regression": True,
                "baseline": baseline_score,
                "current": current_score,
                "delta": round(baseline_score - current_score, 4),
            }
        return None
