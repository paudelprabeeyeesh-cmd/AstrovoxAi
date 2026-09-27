"""Ansible playbook management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnsiblePlaybook:
    playbook_id: str
    name: str
    hosts: List[str]
    tasks: List[Dict[str, Any]]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AnsibleManager:
    def __init__(self) -> None:
        self._playbooks: Dict[str, AnsiblePlaybook] = {}

    def register_playbook(self, playbook: AnsiblePlaybook) -> None:
        self._playbooks[playbook.playbook_id] = playbook

    def get_playbook(self, playbook_id: str) -> Optional[AnsiblePlaybook]:
        return self._playbooks.get(playbook_id)


ansible_manager = AnsibleManager()
