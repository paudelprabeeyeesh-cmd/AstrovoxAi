"""AI context manager."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIContextWindow:
    window_id: str
    user_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    max_tokens: int = 4096
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIContextManager:
    def __init__(self) -> None:
        self._windows: Dict[str, AIContextWindow] = {}

    def create_window(self, user_id: str, max_tokens: int = 4096) -> AIContextWindow:
        window_id = f"{user_id}:default"
        window = AIContextWindow(window_id=window_id, user_id=user_id, max_tokens=max_tokens)
        self._windows[window_id] = window
        return window

    def append_message(self, window_id: str, message: Dict[str, Any]) -> None:
        window = self._windows.get(window_id)
        if window:
            window.messages.append(message)


ai_context_manager = AIContextManager()
