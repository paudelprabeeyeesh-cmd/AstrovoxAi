"""Auto-healing for distributed inference clusters."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ASTROVOX_AI.ai_core.distributed._base import BackgroundService, validate_node_id

logger = logging.getLogger(__name__)


class HealingAction(Enum):
    RESTART_POD = "restart_pod"
    RESCHEDULE = "reschedule"
    SCALE_UP = "scale_up"
    DRAIN = "drain"
    REPLACE = "replace"


@dataclass
class HealthIssue:
    node_id: str
    issue_type: str
    severity: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
    healed: bool = False
    heal_action: Optional[HealingAction] = None


class AutoHealer(BackgroundService):
    def __init__(
        self,
        node_ids: List[str],
        heal_fn: Optional[Callable[[str, HealingAction], bool]] = None,
        check_interval: float = 15.0,
        max_retries: int = 3,
    ):
        super().__init__(check_interval=check_interval)
        if not node_ids:
            raise ValueError("node_ids must not be empty")
        self.node_ids = list(node_ids)
        self.heal_fn = heal_fn
        self.max_retries = max_retries
        self._issues: Dict[str, HealthIssue] = {}
        self._retry_counts: Dict[str, int] = {nid: 0 for nid in node_ids}

    def report_issue(self, node_id: str, issue_type: str, severity: str = "high") -> None:
        validate_node_id(node_id)
        if not issue_type:
            raise ValueError("issue_type must not be empty")
        self._issues[node_id] = HealthIssue(node_id=node_id, issue_type=issue_type, severity=severity)

    def _tick(self) -> None:
        self._detect_and_heal()

    def _detect_and_heal(self) -> None:
        for node_id in self.node_ids:
            if self._is_unhealthy(node_id):
                if node_id not in self._issues or self._issues[node_id].healed:
                    self._issues[node_id] = HealthIssue(node_id=node_id, issue_type="unhealthy", severity="high")
                self._heal_node(node_id)
            else:
                if node_id in self._issues and not self._issues[node_id].healed:
                    self._issues[node_id].healed = True
                    logger.info("Node %s healed successfully", node_id)
                    self._retry_counts[node_id] = 0

    def _is_unhealthy(self, node_id: str) -> bool:
        return node_id in self._issues and not self._issues[node_id].healed

    def _heal_node(self, node_id: str) -> None:
        issue = self._issues[node_id]
        action = self._select_heal_action(issue)
        logger.info("Healing node %s with action %s", node_id, action.value)
        if self.heal_fn:
            success = self.heal_fn(node_id, action)
            if success:
                issue.healed = True
                issue.heal_action = action
                self._retry_counts[node_id] = 0
            else:
                self._retry_counts[node_id] += 1
                if self._retry_counts[node_id] >= self.max_retries:
                    logger.error("Max retries reached for node %s", node_id)
                    issue.severity = "critical"

    def _select_heal_action(self, issue: HealthIssue) -> HealingAction:
        if issue.severity == "critical":
            return HealingAction.REPLACE
        return HealingAction.RESTART_POD

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "issues": [
                {
                    "node_id": i.node_id,
                    "issue_type": i.issue_type,
                    "severity": i.severity,
                    "healed": i.healed,
                    "heal_action": i.heal_action.value if i.heal_action else None,
                }
                for i in self._issues.values()
            ],
            "retry_counts": self._retry_counts,
        }
