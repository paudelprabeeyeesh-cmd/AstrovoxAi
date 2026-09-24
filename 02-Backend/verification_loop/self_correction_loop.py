import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np


@dataclass
class CorrectionResult:
    attempt: int
    success: bool
    error: Optional[str] = None
    model_output: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class CorrectionConfig:
    max_attempts: int = 3
    backoff_factor: float = 2.0
    initial_delay_ms: float = 100.0
    error_threshold: float = 0.5


class SelfCorrectionLoop:
    def __init__(self, config: Optional[CorrectionConfig] = None):
        self.config = config or CorrectionConfig()
        self.history: List[CorrectionResult] = []

    def _delay(self, attempt: int) -> None:
        delay = self.config.initial_delay_ms * (self.config.backoff_factor ** attempt)
        time.sleep(delay / 1000.0)

    def run(
        self,
        error: str,
        model_fn: Callable[[str], str],
        validator_fn: Callable[[str], Dict[str, Any]],
    ) -> Dict[str, Any]:
        self.history = []
        attempt = 0
        current_error = error
        while attempt < self.config.max_attempts:
            start = time.perf_counter()
            try:
                model_output = model_fn(current_error)
            except Exception as exc:
                model_output = ""
                current_error = str(exc)
            duration = (time.perf_counter() - start) * 1000
            validation = validator_fn(model_output)
            success = validation.get("passed", False)
            result = CorrectionResult(
                attempt=attempt + 1,
                success=success,
                error=current_error if not success else None,
                model_output=model_output,
                duration_ms=duration,
            )
            self.history.append(result)
            if success:
                break
            attempt += 1
            self._delay(attempt - 1)
            current_error = f"Attempt {attempt} failed: {validation.get('error', 'unknown')}"
        successes = np.array([1 if r.success else 0 for r in self.history], dtype=np.float64)
        return {
            "converged": self.history[-1].success if self.history else False,
            "attempts": len(self.history),
            "max_attempts": self.config.max_attempts,
            "total_duration_ms": round(sum(r.duration_ms for r in self.history), 3),
            "mean_duration_ms": round(float(np.mean([r.duration_ms for r in self.history])), 3) if self.history else 0.0,
            "success_rate": round(float(np.mean(successes)), 3) if len(successes) else 0.0,
            "final_error": self.history[-1].error if self.history and not self.history[-1].success else None,
            "history": [
                {
                    "attempt": r.attempt,
                    "success": r.success,
                    "error": r.error,
                    "duration_ms": round(r.duration_ms, 3),
                }
                for r in self.history
            ],
        }
