"""Passkey / WebAuthn authentication."""

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import secrets


@dataclass
class WebAuthnCredential:
    credential_id: str
    public_key: str
    algorithm: int
    user_id: str
    created_at: datetime
    last_used: Optional[datetime] = None
    sign_count: int = 0


@dataclass
class WebAuthnChallenge:
    challenge: str
    user_id: str
    expires_at: datetime


class WebAuthnManager:
    _credentials: Dict[str, WebAuthnCredential] = {}
    _challenges: Dict[str, WebAuthnChallenge] = {}

    @classmethod
    def generate_challenge(cls, user_id: str) -> WebAuthnChallenge:
        challenge = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        web_authn_challenge = WebAuthnChallenge(
            challenge=challenge, user_id=user_id, expires_at=expires_at
        )
        cls._challenges[challenge] = web_authn_challenge
        return web_authn_challenge

    @classmethod
    def register_credential(cls, credential_id: str, public_key: str, algorithm: int, user_id: str) -> WebAuthnCredential:
        credential = WebAuthnCredential(
            credential_id=credential_id,
            public_key=public_key,
            algorithm=algorithm,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
        )
        cls._credentials[credential_id] = credential
        return credential

    @classmethod
    def get_credential(cls, credential_id: str) -> Optional[WebAuthnCredential]:
        return cls._credentials.get(credential_id)

    @classmethod
    def validate_challenge(cls, challenge: str) -> bool:
        stored = cls._challenges.get(challenge)
        if not stored or stored.expires_at < datetime.now(timezone.utc):
            return False
        del cls._challenges[challenge]
        return True
