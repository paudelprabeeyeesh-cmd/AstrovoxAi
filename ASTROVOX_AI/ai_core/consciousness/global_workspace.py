import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceContent:
    id: str
    content: Any
    activation: float = 0.0
    source: str = ""
    timestamp: float = 0.0
    duration: float = 0.0


class GlobalWorkspace:
    def __init__(self, capacity: int = 10, threshold: float = 0.5):
        self.capacity = capacity
        self.threshold = threshold
        self.broadcast_queue: deque[WorkspaceContent] = deque(maxlen=capacity)
        self.competitors: list[WorkspaceContent] = []
        self.conscious_content: WorkspaceContent | None = None
        self.broadcast_count: int = 0

    def submit(self, content: WorkspaceContent) -> bool:
        content.timestamp = time.time()
        self.competitors.append(content)
        logger.info("Content submitted: %s (activation=%.2f)", content.id, content.activation)
        return True

    def compete(self) -> WorkspaceContent | None:
        if not self.competitors:
            return None

        winner = max(self.competitors, key=lambda c: c.activation)

        if winner.activation >= self.threshold:
            winner.duration = time.time() - winner.timestamp
            self.broadcast_queue.append(winner)
            self.conscious_content = winner
            self.competitors.clear()
            self.broadcast_count += 1
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
                "duration": self.conscious_content.duration,
                "broadcast_count": self.broadcast_count,
            }
        return {"id": None, "content": None, "activation": 0.0, "duration": 0.0, "broadcast_count": self.broadcast_count}

    def ignite(self, content_id: str, activation: float) -> dict[str, Any]:
        content = WorkspaceContent(id=content_id, content=content_id, activation=activation)
        self.submit(content)
        winner = self.compete()
        if winner:
            return {"status": "ignited", "content_id": winner.id}
        return {"status": "suppressed"}

    def decay(self, decay_rate: float = 0.01):
        if self.conscious_content:
            self.conscious_content.activation = max(0.0, self.conscious_content.activation - decay_rate)
            if self.conscious_content.activation <= 0.0:
                self.conscious_content = None

    def get_workspace_state(self) -> dict[str, Any]:
        return {
            "capacity": self.capacity,
            "threshold": self.threshold,
            "queue_size": len(self.broadcast_queue),
            "competitors": len(self.competitors),
            "broadcast_count": self.broadcast_count,
        }
