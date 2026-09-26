"""Team management for organizations."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Team:
    team_id: str
    org_id: str
    name: str
    members: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TeamManager:
    def __init__(self) -> None:
        self._teams: Dict[str, Team] = {}

    def create(self, org_id: str, name: str) -> Team:
        team_id = uuid.uuid4().hex
        team = Team(team_id=team_id, org_id=org_id, name=name)
        self._teams[team_id] = team
        return team

    def add_member(self, team_id: str, user_id: str) -> None:
        team = self._teams.get(team_id)
        if team and user_id not in team.members:
            team.members.append(user_id)

    def get_team(self, team_id: str) -> Optional[Team]:
        return self._teams.get(team_id)


team_manager = TeamManager()
