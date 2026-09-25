import logging
from typing import Any

logger = logging.getLogger(__name__)


class TheoryOfMindService:
    def infer_state(self, agent_id: str, observations: list[str]) -> dict[str, Any]:
        return {"agent_id": agent_id, "beliefs": {}, "intentions": []}
