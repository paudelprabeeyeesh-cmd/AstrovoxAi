"""System prompt registry."""

from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class PromptCategory(Enum):
    DEFAULT = "default"
    DEVELOPER = "developer"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    SAFETY = "safety"


@dataclass
class SystemPrompt:
    prompt_id: str
    name: str
    content: str
    category: PromptCategory = PromptCategory.DEFAULT
    version: str = "1.0.0"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SystemPromptRegistry:
    _prompts: Dict[str, SystemPrompt] = {}

    @classmethod
    def register(cls, prompt: SystemPrompt) -> None:
        cls._prompts[prompt.prompt_id] = prompt

    @classmethod
    def get(cls, prompt_id: str) -> Optional[SystemPrompt]:
        return cls._prompts.get(prompt_id)

    @classmethod
    def get_active_by_category(cls, category: PromptCategory) -> List[SystemPrompt]:
        return [p for p in cls._prompts.values() if p.active and p.category == category]

    @classmethod
    def search(cls, query: str) -> List[SystemPrompt]:
        query_lower = query.lower()
        return [
            p for p in cls._prompts.values()
            if query_lower in p.name.lower() or query_lower in p.content.lower() or query_lower in p.description.lower()
        ]

    @classmethod
    def list_all(cls) -> List[SystemPrompt]:
        return list(cls._prompts.values())
