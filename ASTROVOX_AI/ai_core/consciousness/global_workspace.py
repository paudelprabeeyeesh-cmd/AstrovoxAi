import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceContent:
    id: str
    content: Any
    activation: float = 0.0
    source: str = ""
    timestamp: float = 0.0


class GlobalWorkspace:
    def __init__(self, capacity: int = 10, threshold: float = 0.5):
        self.capacity = capacity
        self.threshold = threshold
        self.broadcast_queue: deque[WorkspaceContent] = deque(maxlen=capacity)
        self.competitors: list[WorkspaceContent] = []
        self.conscious_content: WorkspaceContent | None = None

    def submit(self, content: WorkspaceContent) -> bool:
        self.competitors.append(content)
        logger.info("Content submitted: %s (activation=%.2f)", content.id, content.activation)
        return True

    def compete(self) -> WorkspaceContent | None:
        if not self.competitors:
            return None

        winner = max(self.competitors, key=lambda c: c.activation)

        if winner.activation >= self.threshold:
            self.broadcast_queue.append(winner)
            self.conscious_content = winner
            self.competitors.clear()
            logger.info("Broadcast winner: %s", winner.id)
            return winner

        self.competitors.clear()
        return None

    def get_conscious_content(self) -> dict[str, Any]:
        if self.conscious_content:
            return {
                "id": self.conscious_content.id,
                "content": self.conscious_content.content,
                "activation": self.conscious_content.activation,
            }
        return {"id": None, "content": None, "activation": 0.0}

    def ignite(self, content_id: str, activation: float) -> dict[str, Any]:
        content = WorkspaceContent(id=content_id, content=content_id, activation=activation)
        self.submit(content)
        winner = self.compete()
        if winner:
            return {"status": "ignited", "content_id": winner.id}
        return {"status": "suppressed"}
