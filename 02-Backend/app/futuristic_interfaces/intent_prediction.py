import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class IntentPredictionService:
    def __init__(self) -> None:
        self._predictions: dict[str, dict[str, Any]] = {}

    def predict(self, history: list[dict[str, Any]], current_context: dict[str, Any]) -> dict[str, Any]:
        intent_id = str(uuid.uuid4())
        recent_actions = [h.get("action", "") for h in history[-5:]] if history else []
        context_keys = list(current_context.keys()) if current_context else []

        if "search" in recent_actions:
            goal = "continue_search"
            confidence = 0.8
        elif "create" in recent_actions:
            goal = "continue_creation"
            confidence = 0.75
        elif context_keys:
            goal = f"explore_{context_keys[0]}"
            confidence = 0.6
        else:
            goal = "unknown"
            confidence = 0.4

        result = {
            "intent_id": intent_id,
            "goal": goal,
            "confidence": confidence,
            "recent_actions": recent_actions,
            "context_keys": context_keys,
            "timestamp": time.time(),
        }
        self._predictions[intent_id] = result
        return result

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        items = sorted(self._predictions.values(), key=lambda x: x["timestamp"], reverse=True)
        return items[:limit]
