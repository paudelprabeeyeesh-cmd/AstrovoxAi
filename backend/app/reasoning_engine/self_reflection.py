"""Self-reflection for reasoning improvement."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReflectionResult:
    task_id: str
    original_output: str
    critique: str
    improved_output: str
    score_delta: float
    reflected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SelfReflection:
    def __init__(self) -> None:
        self._results: Dict[str, ReflectionResult] = {}

    def reflect(self, task_id: str, output: str, critique: str) -> ReflectionResult:
        improved = f"{output} [refined: {critique}]"
        result = ReflectionResult(
            task_id=task_id,
            original_output=output,
            critique=critique,
            improved_output=improved,
            score_delta=0.1,
        )
        self._results[task_id] = result
        return result

    def get_reflection(self, task_id: str) -> Optional[ReflectionResult]:
        return self._results.get(task_id)


self_reflection = SelfReflection()
