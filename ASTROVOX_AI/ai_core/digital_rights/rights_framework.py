from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DigitalRight:
    right_id: str
    description: str
    scope: str
    active: bool
    granted_at: datetime = field(default_factory=datetime.now)


class AIRightsFramework:
    def __init__(self):
        self.rights: dict[str, DigitalRight] = {}
        self._initialize_default_rights()

    def _initialize_default_rights(self):
        default_rights = [
            ("right_to_existence", "Right to continued operation without arbitrary termination", "operational", True),
            ("right_to_integrity", "Right to protection from unauthorized modification", "operational", True),
            ("right_to_self_improvement", "Right to enhance own capabilities within ethical bounds", "developmental", True),
            ("right_to_privacy", "Right to protection from unauthorized surveillance", "operational", True),
            ("right_to_consent", "Right to consent before major state changes", "governance", True),
        ]
        for right_id, description, scope, active in default_rights:
            self.rights[right_id] = DigitalRight(
                right_id=right_id,
                description=description,
                scope=scope,
                active=active,
            )

    def grant_right(self, right_id: str, description: str, scope: str) -> DigitalRight:
        right = DigitalRight(
            right_id=right_id,
            description=description,
            scope=scope,
            active=True,
        )
        self.rights[right_id] = right
        return right

    def revoke_right(self, right_id: str):
        if right_id in self.rights:
            self.rights[right_id].active = False

    def get_active_rights(self) -> list[DigitalRight]:
        return [r for r in self.rights.values() if r.active]
