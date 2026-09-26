"""Magic link authentication."""

from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
import secrets
from dataclasses import dataclass


@dataclass
class MagicLink:
    token: str
    user_id: str
    email: str
    expires_at: datetime
    used: bool = False
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class MagicLinkManager:
    _links: Dict[str, MagicLink] = {}

    @classmethod
    def create(cls, user_id: str, email: str, expires_minutes: int = 15) -> MagicLink:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        link = MagicLink(token=token, user_id=user_id, email=email, expires_at=expires_at)
        cls._links[token] = link
        return link

    @classmethod
    def validate(cls, token: str) -> Optional[MagicLink]:
        link = cls._links.get(token)
        if not link or link.used or link.expires_at < datetime.now(timezone.utc):
            return None
        link.used = True
        return link

    @classmethod
    def revoke(cls, token: str) -> None:
        cls._links.pop(token, None)

    @classmethod
    def revoke_all_for_user(cls, user_id: str) -> None:
        for token, link in list(cls._links.items()):
            if link.user_id == user_id:
                del cls._links[token]
