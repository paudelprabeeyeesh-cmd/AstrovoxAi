"""Auto-healing for distributed inference clusters."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

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


class AutoHealer:
    def __init__(
        self,
        node_ids: List[str],
        heal_fn: Optional[Callable[[str, HealingAction], bool]] = None,
        check_interval: float = 15.0,
        max_retries: int = 3,
    ):
        self.node_ids = node_ids
        self.heal_fn = heal_fn
        self.check_interval = check_interval
        self.max_retries = max_retries
        self._issues: Dict[str, HealthIssue] = {}
        self._retry_counts: Dict[str, int] = {nid: 0 for nid in node_ids}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._healing_loop, daemon=True)
        self._thread.start()
        logger.info("Auto-healer started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Auto-healer stopped")

    def _healing_loop(self) -> None:
        while self._running:
            try:
                self._detect_and_heal()
            except Exception:
                logger.exception("Auto-healing error")
            time.sleep(self.check_interval)

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
        if issue.issue_type == "unhealthy":
            return HealingAction.RESTART_POD
        return HealingAction.RESTART_POD

    def report_issue(self, node_id: str, issue_type: str, severity: str = "high") -> None:
        self._issues[node_id] = HealthIssue(node_id=node_id, issue_type=issue_type, severity=severity)

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
