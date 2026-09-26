"""Template generator for projects."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProjectTemplate:
    template_id: str
    name: str
    description: str
    files: Dict[str, str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class TemplateGenerator:
    def __init__(self) -> None:
        self._templates: Dict[str, ProjectTemplate] = {}

    def create_template(self, template: ProjectTemplate) -> ProjectTemplate:
        template.template_id = template.template_id or uuid.uuid4().hex
        self._templates[template.template_id] = template
        return template

    def get_template(self, template_id: str) -> Optional[ProjectTemplate]:
        return self._templates.get(template_id)

    def list_templates(self) -> List[ProjectTemplate]:
        return list(self._templates.values())


template_generator = TemplateGenerator()
