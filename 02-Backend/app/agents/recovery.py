from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AgentRecovery:
    def __init__(self):
        self.recovery_strategies: List[Any] = []
        self.recovery_history: List[Dict[str, Any]] = []

    def register_strategy(self, strategy: Any) -> None:
        self.recovery_strategies.append(strategy)

    def attempt_recovery(self, agent_id: str, failure: Dict[str, Any]) -> Dict[str, Any]:
        for strategy in self.recovery_strategies:
            try:
                result = strategy(agent_id, failure)
                if result.get("recovered"):
                    record = {"agent_id": agent_id, "strategy": getattr(strategy, "__name__", str(strategy)), "success": True}
                    self.recovery_history.append(record)
                    return result
            except Exception as exc:
                logger.warning("Recovery strategy failed: %s", exc)
        record = {"agent_id": agent_id, "strategy": None, "success": False}
        self.recovery_history.append(record)
        return {"recovered": False, "error": "All recovery strategies exhausted"}

    def checkpoint(self, agent_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"agent_id": agent_id, "state": state, "timestamp": __import__("datetime").datetime.utcnow().isoformat()}

    def restore(self, checkpoint: Dict[str, Any]) -> Dict[str, Any]:
        return {"agent_id": checkpoint.get("agent_id"), "state": checkpoint.get("state"), "restored": True}
