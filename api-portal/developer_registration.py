"""
Developer registration for AstrovoxAI.
Manages developer accounts, onboarding, and team management.
"""

import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Developer:
    developer_id: str
    email: str
    name: str
    company: Optional[str]
    role: str = "developer"
    verified: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "developer_id": self.developer_id,
            "email": self.email,
            "name": self.name,
            "company": self.company,
            "role": self.role,
            "verified": self.verified,
            "created_at": self.created_at.isoformat(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


@dataclass
class DeveloperInvite:
    invite_id: str
    email: str
    inviter_id: str
    role: str
    token: str
    expires_at: datetime
    accepted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invite_id": self.invite_id,
            "email": self.email,
            "inviter_id": self.inviter_id,
            "role": self.role,
            "expires_at": self.expires_at.isoformat(),
            "accepted": self.accepted,
        }


class DeveloperRegistry:
    """Manages developer accounts and registration."""

    def __init__(self):
        self._developers: Dict[str, Developer] = {}
        self._invites: Dict[str, DeveloperInvite] = {}

    def register(
        self,
        email: str,
        name: str,
        password: str,
        company: Optional[str] = None,
    ) -> Developer:
        if any(d.email == email for d in self._developers.values()):
            raise ValueError("Email already registered")
        developer = Developer(
            developer_id=str(uuid.uuid4()),
            email=email,
            name=name,
            company=company,
        )
        self._developers[developer.developer_id] = developer
        logger.info("Registered developer %s (%s)", developer.developer_id, email)
        return developer

    def get_developer(self, developer_id: str) -> Optional[Developer]:
        return self._developers.get(developer_id)

    def get_developer_by_email(self, email: str) -> Optional[Developer]:
        for d in self._developers.values():
            if d.email == email:
                return d
        return None

    def verify_email(self, developer_id: str) -> Developer:
        developer = self._developers.get(developer_id)
        if not developer:
            raise ValueError("Developer not found")
        developer.verified = True
        return developer

    def invite_developer(
        self,
        email: str,
        inviter_id: str,
        role: str = "member",
        expires_in_hours: int = 72,
    ) -> DeveloperInvite:
        invite = DeveloperInvite(
            invite_id=str(uuid.uuid4()),
            email=email,
            inviter_id=inviter_id,
            role=role,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours),
        )
        self._invites[invite.invite_id] = invite
        logger.info("Created invite %s for %s", invite.invite_id, email)
        return invite

    def accept_invite(self, token: str, name: str, password: str) -> Developer:
        for invite in self._invites.values():
            if invite.token == token and not invite.accepted:
                if datetime.utcnow() > invite.expires_at:
                    raise ValueError("Invite expired")
                invite.accepted = True
                developer = Developer(
                    developer_id=str(uuid.uuid4()),
                    email=invite.email,
                    name=name,
                    company=None,
                )
                self._developers[developer.developer_id] = developer
                return developer
        raise ValueError("Invalid invite token")
