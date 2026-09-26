"""Multi-factor authentication service."""
from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MFASecret:
    user_id: str
    secret: str
    method: str
    backup_codes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None


class MFAService:
    def __init__(self) -> None:
        self._secrets: Dict[str, MFASecret] = {}
        self._attempts: Dict[str, List[Dict[str, Any]]] = {}

    def enroll(self, user_id: str, method: str, secret: str, backup_codes: Optional[List[str]] = None) -> MFASecret:
        mfa_secret = MFASecret(user_id=user_id, secret=secret, method=method, backup_codes=backup_codes or [])
        self._secrets[user_id] = mfa_secret
        logger.info("Enrolled MFA for user %s via %s", user_id, method)
        return mfa_secret

    def verify(self, user_id: str, code: str) -> bool:
        secret = self._secrets.get(user_id)
        if not secret:
            return False
        valid = code == secret.secret or code in secret.backup_codes
        if valid:
            secret.last_used_at = datetime.now(timezone.utc)
            self._attempts.setdefault(user_id, []).append({"success": True, "at": datetime.now(timezone.utc).isoformat()})
        else:
            self._attempts.setdefault(user_id, []).append({"success": False, "at": datetime.now(timezone.utc).isoformat()})
        return valid

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        return [secrets.token_hex(4) for _ in range(count)]

    def disable(self, user_id: str) -> None:
        self._secrets.pop(user_id, None)

    def get_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        secret = self._secrets.get(user_id)
        if not secret:
            return None
        return {
            "user_id": secret.user_id,
            "method": secret.method,
            "enabled": True,
            "backup_codes_remaining": len(secret.backup_codes),
            "last_used_at": secret.last_used_at.isoformat() if secret.last_used_at else None,
        }


mfa_service = MFAService()
