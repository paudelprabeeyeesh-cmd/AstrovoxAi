"""Prompt templates with versioning."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    name: str
    version: str
    template: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class PromptRegistry:
    """Version-controlled prompt templates."""

    def __init__(self) -> None:
        self._templates: Dict[str, Dict[str, PromptTemplate]] = {}

    def register(self, template: PromptTemplate) -> None:
        self._templates.setdefault(template.name, {})[template.version] = template
        logger.info(f"Registered prompt: {template.name}@{template.version}")

    def get(self, name: str, version: str = "latest") -> Optional[PromptTemplate]:
        versions = self._templates.get(name)
        if not versions:
            return None
        if version == "latest":
            return max(versions.values(), key=lambda t: t.created_at)
        return versions.get(version)

    def render(self, name: str, variables: Dict[str, Any], version: str = "latest") -> Optional[str]:
        template = self.get(name, version)
        if not template:
            return None
        try:
            return template.template.format(**variables)
        except KeyError as exc:
            logger.error(f"Missing variable in prompt {name}: {exc}")
            return None


_prompt_registry = PromptRegistry()


def get_prompt_registry() -> PromptRegistry:
    return _prompt_registry
