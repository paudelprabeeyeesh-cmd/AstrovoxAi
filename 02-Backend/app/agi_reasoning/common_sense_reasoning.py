import logging
from typing import Any

logger = logging.getLogger(__name__)


class CommonSenseReasoningService:
    def __init__(self):
        self.beliefs: dict[str, Any] = {}

    def add_belief(self, statement: str, belief: Any) -> None:
        self.beliefs[statement] = belief

    def query(self, statement: str) -> Any:
        return self.beliefs.get(statement)
