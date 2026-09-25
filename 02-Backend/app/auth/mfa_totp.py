"""MFA/TOTP authentication."""

from typing import Dict, Optional, Any
from datetime import datetime, timezone
import pyotp
import base64
import secrets
from dataclasses import dataclass


@dataclass
class TOTPSecret:
    user_id: str
    secret: str
    issuer: str = "AstrovoxAi"
    confirmed: bool = False
    backup_codes: list[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.backup_codes is None:
            self.backup_codes = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class TOTPManager:
    _secrets: Dict[str, TOTPSecret] = {}

    @classmethod
    def create_secret(cls, user_id: str, issuer: str = "AstrovoxAi") -> tuple[str, str]:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret, issuer=issuer)
        provisioning_uri = totp.provisioning_uri(name=user_id, issuer_name=issuer)
        return secret, provisioning_uri

    @classmethod
    def store(cls, user_id: str, secret: str, issuer: str = "AstrovoxAi") -> TOTPSecret:
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        totp_secret = TOTPSecret(user_id=user_id, secret=secret, issuer=issuer, backup_codes=backup_codes)
        cls._secrets[user_id] = totp_secret
        return totp_secret

    @classmethod
    def verify(cls, user_id: str, token: str) -> bool:
        secret = cls._secrets.get(user_id)
        if not secret:
            return False
        totp = pyotp.TOTP(secret.secret, issuer=secret.issuer)
        if totp.verify(token):
            secret.confirmed = True
            return True
        return False

    @classmethod
    def verify_backup(cls, user_id: str, code: str) -> bool:
        secret = cls._secrets.get(user_id)
        if not secret:
            return False
        normalized = code.replace("-", "").upper()
        if normalized in secret.backup_codes:
            secret.backup_codes.remove(normalized)
            return True
        return False

    @classmethod
    def get_secret(cls, user_id: str) -> Optional[TOTPSecret]:
        return cls._secrets.get(user_id)
