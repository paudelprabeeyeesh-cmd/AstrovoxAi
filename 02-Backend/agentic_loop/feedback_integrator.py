from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Feedback:
    observation: Optional[str] = None
    error: Optional[str] = None
    step_index: Optional[int] = None
    metadata: Dict[str, Any] = None


class FeedbackIntegrator:
    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self.retry_counts: Dict[int, int] = {}

    def integrate(self, state: Any, feedback: Feedback) -> Any:
        if feedback.step_index is not None:
            self.retry_counts[feedback.step_index] = self.retry_counts.get(feedback.step_index, 0) + 1

        if hasattr(state, "metadata"):
            key = f"feedback_{feedback.step_index}"
            state.metadata[key] = {
                "observation": feedback.observation,
                "error": feedback.error,
                "timestamp": datetime.utcnow().isoformat(),
                "retry_count": self.retry_counts.get(feedback.step_index, 0),
            }

        return state

    def should_retry(self, step_index: int) -> bool:
        return self.retry_counts.get(step_index, 0) < self.max_retries
