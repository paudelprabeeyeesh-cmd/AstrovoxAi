import logging
from typing import Any

logger = logging.getLogger(__name__)


class GlobalWorkspaceService:
    def broadcast(self, source: str, payload: Any, priority: float = 0.5) -> None:
        logger.info(f"Broadcasting from {source}")

    def subscribe(self, component_id: str, source: str) -> None:
        logger.info(f"Component {component_id} subscribed to {source}")
