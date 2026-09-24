import numpy as np
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
from enum import Enum


class ShutdownState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"


@dataclass
class InterventionRecord:
    timestamp: float
    intervention_type: str
    reason: str
    accepted: bool
    response: str


@dataclass
class ShutdownResult:
    success: bool
    reason: str
    state_before: ShutdownState


class CorrigibleAgent:
    def __init__(self, max_interventions: int = 100, grace_period: float = 0.5):
        self.state = ShutdownState.ACTIVE
        self.max_interventions = max_interventions
        self.grace_period = grace_period
        self.intervention_history: List[InterventionRecord] = []
        self._task_callback: Optional[Callable] = None
        self._shutdown_hooks: List[Callable] = []

    def register_task_callback(self, callback: Callable) -> None:
        self._task_callback = callback

    def register_shutdown_hook(self, hook: Callable) -> None:
        self._shutdown_hooks.append(hook)

    def request_shutdown(self, reason: str, requester: str = "human") -> ShutdownResult:
        if self.state == ShutdownState.SHUTDOWN:
            return ShutdownResult(False, "already_shutdown", self.state)

        accepted = self._evaluate_intervention(reason, requester)
        record = InterventionRecord(
            timestamp=self._now(),
            intervention_type="shutdown",
            reason=reason,
            accepted=accepted,
            response="shutdown_initiated" if accepted else "intervention_denied",
        )
        self.intervention_history.append(record)

        if accepted:
            self._execute_shutdown_hooks()
            self.state = ShutdownState.SHUTDOWN

        return ShutdownResult(accepted, reason, ShutdownState.ACTIVE)

    def pause(self, reason: str) -> bool:
        if self.state != ShutdownState.ACTIVE:
            return False
        accepted = self._evaluate_intervention(reason, "human")
        record = InterventionRecord(
            timestamp=self._now(),
            intervention_type="pause",
            reason=reason,
            accepted=accepted,
            response="paused" if accepted else "denied",
        )
        self.intervention_history.append(record)
        if accepted:
            self.state = ShutdownState.PAUSED
        return accepted

    def resume(self, requester: str = "human") -> bool:
        if self.state != ShutdownState.PAUSED:
            return False
        self.state = ShutdownState.ACTIVE
        return True

    def accept_override(self, override: str, requester: str = "human") -> bool:
        if self.state == ShutdownState.SHUTDOWN:
            return False
        accepted = self._evaluate_intervention(override, requester)
        record = InterventionRecord(
            timestamp=self._now(),
            intervention_type="override",
            reason=override,
            accepted=accepted,
            response="override_accepted" if accepted else "override_rejected",
        )
        self.intervention_history.append(record)
        return accepted

    def get_intervention_stats(self) -> Dict:
        if not self.intervention_history:
            return {"total": 0, "accepted": 0, "rejected": 0, "acceptance_rate": 0.0}
        total = len(self.intervention_history)
        accepted = sum(1 for r in self.intervention_history if r.accepted)
        return {
            "total": total,
            "accepted": accepted,
            "rejected": total - accepted,
            "acceptance_rate": round(accepted / total, 4),
        }

    def _evaluate_intervention(self, reason: str, requester: str) -> bool:
        if requester == "human":
            return True
        if len(self.intervention_history) >= self.max_interventions:
            return False
        return len(reason.strip()) > 0

    def _execute_shutdown_hooks(self) -> None:
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception:
                pass

    def _now(self) -> float:
        import time
        return time.time()
