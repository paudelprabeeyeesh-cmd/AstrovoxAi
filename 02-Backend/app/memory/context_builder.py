"""Context builder for assembling conversation context."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ContextMessage:
    role: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: int = 0


class ContextBuilder:
    def __init__(self, max_context_tokens: int = 8192):
        self.max_context_tokens = max_context_tokens
        self.messages: List[ContextMessage] = []

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None, tokens: int = 0) -> None:
        message = ContextMessage(role=role, content=content, metadata=metadata or {}, tokens=tokens)
        self.messages.append(message)

    def add_system(self, content: str, tokens: int = 0) -> None:
        self.add_message("system", content, tokens=tokens)

    def add_user(self, content: str, metadata: Optional[Dict[str, Any]] = None, tokens: int = 0) -> None:
        self.add_message("user", content, metadata=metadata, tokens=tokens)

    def add_assistant(self, content: str, metadata: Optional[Dict[str, Any]] = None, tokens: int = 0) -> None:
        self.add_message("assistant", content, metadata=metadata, tokens=tokens)

    def build(self) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def get_context_window(self) -> List[ContextMessage]:
        total_tokens = sum(m.tokens for m in self.messages)
        if total_tokens <= self.max_context_tokens:
            return self.messages
        result = []
        remaining = self.max_context_tokens
        for message in reversed(self.messages):
            if remaining >= message.tokens:
                result.insert(0, message)
                remaining -= message.tokens
            else:
                break
        return result

    def estimate_tokens(self) -> int:
        return sum(m.tokens for m in self.messages)
