import logging
from typing import Any

logger = logging.getLogger(__name__)


class ActiveInferenceService:
    def infer_action(self, observation: dict[str, Any], policies: list[dict[str, Any]]) -> dict[str, Any]:
        best = max(policies, key=lambda p: p.get("value", 0.0))
        return {"action": best, "expected_free_energy": 0.1}
