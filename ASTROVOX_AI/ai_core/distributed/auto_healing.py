"""Auto-healing for distributed inference nodes."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealingAction(Enum):
    RESTART = "restart"
    RESCHEDULE = "reschedule"
    SCALE_UP = "scale_up"
    DRAIN = "drain"


@dataclass
class HealthEvent:
    node_id: str
    event_type: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    action: Optional[HealingAction] = None


class AutoHealer:
    def __init__(
        self,
        node_ids: List[str],
        health_check_fn: Callable[[str], Dict[str, Any]],
        heal_fn: Callable[[str, HealingAction], bool],
    ):
        self.node_ids = node_ids
        self.health_check_fn = health_check_fn
        self.heal_fn = heal_fn
        self._event_history: List[HealthEvent] = []
        self._node_states: Dict[str, Dict[str, Any]] = {nid: {"failures": 0, "last_failure": None, "healing": False} for nid in node_ids}
        self._running = False

    def start(self) -> None:
        self._running = True
        logger.info("Auto-healer started")

    def stop(self) -> None:
        self._running = False
        logger.info("Auto-healer stopped")

    def run_healing_cycle(self) -> List[HealthEvent]:
        events = []
        for node_id in self.node_ids:
            try:
                health = self.health_check_fn(node_id)
                healthy = health.get("healthy", False)
            except Exception:
                healthy = False
                health = {"error": "health check failed"}
            node_state = self._node_states[node_id]
            if not healthy:
                node_state["failures"] += 1
                node_state["last_failure"] = datetime.utcnow()
                action = self._determine_healing_action(node_id, node_state)
                event = HealthEvent(
                    node_id=node_id,
                    event_type="unhealthy",
                    timestamp=datetime.utcnow(),
                    details=health,
                    action=action,
                )
                self._event_history.append(event)
                if action and not node_state["healing"]:
                    node_state["healing"] = True
                    success = self.heal_fn(node_id, action)
                    event.details["healed"] = success
                    node_state["healing"] = False
                    if success:
                        node_state["failures"] = 0
                events.append(event)
            else:
                node_state["failures"] = max(0, node_state["failures"] - 1)
        return events

    def _determine_healing_action(self, node_id: str, node_state: Dict[str, Any]) -> Optional[HealingAction]:
        failures = node_state["failures"]
        if failures == 1:
            return HealingAction.RESTART
        if failures == 2:
            return HealingAction.RESCHEDULE
        if failures >= 3:
            return HealingAction.DRAIN
        return None

    def get_healing_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [
            {
                "node_id": e.node_id,
                "event_type": e.event_type,
                "action": e.action.value if e.action else None,
                "timestamp": e.timestamp.isoformat(),
                "details": e.details,
            }
            for e in self._event_history[-limit:]
        ]

    def get_node_health(self) -> Dict[str, Any]:
        return {
            node_id: {
                "failures": state["failures"],
                "healing": state["healing"],
                "last_failure": state["last_failure"].isoformat() if state["last_failure"] else None,
            }
            for node_id, state in self._node_states.items()
        }
