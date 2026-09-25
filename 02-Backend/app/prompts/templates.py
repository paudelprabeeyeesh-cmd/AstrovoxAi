"""Prompt templates with variable substitution."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
import re


@dataclass
class PromptTemplate:
    name: str
    template: str
    version: str = "1.0.0"
    description: str = ""
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PromptTemplateRegistry:
    _templates: Dict[str, PromptTemplate] = {}

    @classmethod
    def register(cls, template: PromptTemplate) -> None:
        cls._templates[template.name] = template

    @classmethod
    def render(cls, name: str, variables: Dict[str, Any]) -> Optional[str]:
        template = cls._templates.get(name)
        if not template:
            return None
        try:
            return template.template.format(**variables)
        except KeyError as e:
            return None

    @classmethod
    def get(cls, name: str) -> Optional[PromptTemplate]:
        return cls._templates.get(name)

    @classmethod
    def list_templates(cls) -> List[PromptTemplate]:
        return list(cls._templates.values())

    @classmethod
    def extract_variables(cls, template_str: str) -> List[str]:
        return re.findall(r'\{([^}]+)\}', template_str)
