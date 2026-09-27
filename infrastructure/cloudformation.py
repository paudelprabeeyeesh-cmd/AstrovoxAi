"""CloudFormation template management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CloudFormationTemplate:
    template_id: str
    name: str
    resources: Dict[str, Any]
    parameters: Dict[str, Any] = field(default_factory=dict)


class CloudFormationManager:
    def __init__(self) -> None:
        self._templates: Dict[str, CloudFormationTemplate] = {}

    def register_template(self, template: CloudFormationTemplate) -> None:
        self._templates[template.template_id] = template


cloud_formation_manager = CloudFormationManager()
