"""Incident response management."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class IncidentPlaybook:
    playbook_id: str
    name: str
    steps: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class IncidentResponseManager:
    def __init__(self) -> None:
        self._playbooks: Dict[str, IncidentPlaybook] = {}

    def create_playbook(self, playbook: IncidentPlaybook) -> IncidentPlaybook:
        playbook.playbook_id = playbook.playbook_id or uuid.uuid4().hex
        self._playbooks[playbook.playbook_id] = playbook
        return playbook

    def get_playbook(self, playbook_id: str) -> Optional[IncidentPlaybook]:
        return self._playbooks.get(playbook_id)


incident_response_manager = IncidentResponseManager()
