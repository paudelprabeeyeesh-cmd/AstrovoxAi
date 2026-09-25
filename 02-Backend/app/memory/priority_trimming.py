"""Priority-based context trimming."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class MessagePriority(Enum):
    SYSTEM = 100
    CRITICAL = 80
    HIGH = 60
    MEDIUM = 40
    LOW = 20
    HISTORICAL = 10


@dataclass
class PrioritizedMessage:
    role: str
    content: str
    priority: MessagePriority
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: int = 0


class PriorityTrimmer:
    @staticmethod
    def trim(messages: List[PrioritizedMessage], max_tokens: int) -> List[PrioritizedMessage]:
        sorted_messages = sorted(messages, key=lambda m: m.priority.value, reverse=True)
        result = []
        used_tokens = 0
        for message in sorted_messages:
            if used_tokens + message.tokens <= max_tokens:
                result.append(message)
                used_tokens += message.tokens
        result.sort(key=lambda m: m.timestamp)
        return result
