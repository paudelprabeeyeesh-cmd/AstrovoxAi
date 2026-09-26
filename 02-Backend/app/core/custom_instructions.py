"""
Custom instructions and user preferences.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CustomInstruction:
    instruction_id: str
    user_id: str
    content: str
    category: str = "general"
    enabled: bool = True
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserPreferences:
    user_id: str
    theme: str = "dark"
    language: str = "en"
    timezone: str = "UTC"
    default_model: str = "astrovox-1b"
    temperature: float = 0.7
    max_tokens: int = 2048
    streaming_enabled: bool = True
    notifications_enabled: bool = True
    custom_instructions: List[CustomInstruction] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "theme": self.theme,
            "language": self.language,
            "timezone": self.timezone,
            "default_model": self.default_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "streaming_enabled": self.streaming_enabled,
            "notifications_enabled": self.notifications_enabled,
        }


class CustomInstructionManager:
    """Manage custom instructions for users."""

    def __init__(self):
        self.instructions: Dict[str, List[CustomInstruction]] = {}
        self.user_preferences: Dict[str, UserPreferences] = {}

    def add_instruction(self, user_id: str, content: str, category: str = "general", priority: int = 0) -> CustomInstruction:
        instruction_id = str(__import__("uuid").uuid4())
        instruction = CustomInstruction(instruction_id=instruction_id, user_id=user_id, content=content, category=category, priority=priority)
        self.instructions.setdefault(user_id, []).append(instruction)
        return instruction

    def get_user_instructions(self, user_id: str, category: Optional[str] = None) -> List[CustomInstruction]:
        instructions = self.instructions.get(user_id, [])
        if category:
            instructions = [i for i in instructions if i.category == category]
        return sorted(instructions, key=lambda x: x.priority, reverse=True)

    def update_instruction(self, instruction_id: str, content: Optional[str] = None, enabled: Optional[bool] = None, priority: Optional[int] = None) -> bool:
        for user_instructions in self.instructions.values():
            for instruction in user_instructions:
                if instruction.instruction_id == instruction_id:
                    if content is not None:
                        instruction.content = content
                    if enabled is not None:
                        instruction.enabled = enabled
                    if priority is not None:
                        instruction.priority = priority
                    instruction.updated_at = datetime.now()
                    return True
        return False

    def delete_instruction(self, instruction_id: str) -> bool:
        for user_id, instructions in self.instructions.items():
            for i, instruction in enumerate(instructions):
                if instruction.instruction_id == instruction_id:
                    instructions.pop(i)
                    return True
        return False

    def get_instructions_as_prompt(self, user_id: str) -> str:
        instructions = self.get_user_instructions(user_id)
        if not instructions:
            return ""
        parts = []
        for i, instruction in enumerate(instructions, 1):
            parts.append(f"{i}. {instruction.content}")
        return "\n".join(parts)


class UserPreferencesManager:
    """Manage user preferences."""

    def __init__(self):
        self.preferences: Dict[str, UserPreferences] = {}

    def get_preferences(self, user_id: str) -> UserPreferences:
        if user_id not in self.preferences:
            self.preferences[user_id] = UserPreferences(user_id=user_id)
        return self.preferences[user_id]

    def update_preferences(self, user_id: str, **kwargs) -> UserPreferences:
        prefs = self.get_preferences(user_id)
        for key, value in kwargs.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        prefs.updated_at = datetime.now()
        return prefs

    def set_custom_instruction(self, user_id: str, content: str, category: str = "general") -> CustomInstruction:
        instruction_manager = CustomInstructionManager()
        return instruction_manager.add_instruction(user_id, content, category)

    def get_system_prompt_with_instructions(self, user_id: str, base_prompt: str) -> str:
        instruction_manager = CustomInstructionManager()
        custom_instructions = instruction_manager.get_instructions_as_prompt(user_id)
        if custom_instructions:
            return f"{base_prompt}\n\nCustom Instructions:\n{custom_instructions}"
        return base_prompt


instruction_manager = CustomInstructionManager()
preferences_manager = UserPreferencesManager()
