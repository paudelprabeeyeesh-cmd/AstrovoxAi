import logging
from typing import Any

logger = logging.getLogger(__name__)


class IntentPredictionService:
    def predict(self, history: list[dict[str, Any]], current_context: dict[str, Any]) -> dict[str, Any]:
        return {"intent_id": "intent_1", "goal": "unknown", "confidence": 0.5}
