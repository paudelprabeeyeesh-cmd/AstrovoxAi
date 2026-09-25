import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceMessage:
    source: str
    payload: Any
    priority: float = 0.5
    timestamp: str = ""


class GlobalWorkspace:
    def __init__(self):
        self.messages: list[WorkspaceMessage] = []
        self.subscribers: dict[str, list[str]] = {}

    def broadcast(self, message: WorkspaceMessage) -> None:
        self.messages.append(message)

    def subscribe(self, component_id: str, source: str) -> None:
        self.subscribers.setdefault(source, []).append(component_id)
