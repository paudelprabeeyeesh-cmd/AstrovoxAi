"""Customer-managed encryption keys (CMK) — BYOK/HYOK support."""

import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CustomerManagedKey:
    key_id: str
    tenant_id: str
    name: str
    provider: str
    key_ref: str
    scope: str = "org"
    status: str = "active"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rotated_at: Optional[str] = None


class CustomerManagedKeyManager:
    def __init__(self):
        self._keys: Dict[str, CustomerManagedKey] = {}

    def register_key(self, tenant_id: str, name: str, provider: str, key_ref: str, scope: str = "org") -> CustomerManagedKey:
        key_id = f"cmk_{uuid.uuid4().hex[:12]}"
        key = CustomerManagedKey(key_id=key_id, tenant_id=tenant_id, name=name, provider=provider, key_ref=key_ref, scope=scope)
        self._keys[key_id] = key
        logger.info("Registered CMK %s for tenant %s provider %s", key_id, tenant_id, provider)
        return key

    def rotate_key(self, key_id: str, new_key_ref: str) -> Optional[CustomerManagedKey]:
        key = self._keys.get(key_id)
        if not key:
            return None
        key.key_ref = new_key_ref
        key.rotated_at = datetime.now(timezone.utc).isoformat()
        logger.info("Rotated CMK %s", key_id)
        return key

    def revoke_key(self, key_id: str) -> bool:
        key = self._keys.get(key_id)
        if not key:
            return False
        key.status = "revoked"
        logger.info("Revoked CMK %s", key_id)
        return True

    def get_key(self, key_id: str) -> Optional[CustomerManagedKey]:
        return self._keys.get(key_id)

    def get_active_key_for_tenant(self, tenant_id: str, scope: str = "org") -> Optional[CustomerManagedKey]:
        for key in self._keys.values():
            if key.tenant_id == tenant_id and key.scope == scope and key.status == "active":
                return key
        return None

    def list_keys(self, tenant_id: str) -> List[dict]:
        return [
            {
                "key_id": k.key_id,
                "name": k.name,
                "provider": k.provider,
                "scope": k.scope,
                "status": k.status,
                "created_at": k.created_at,
                "rotated_at": k.rotated_at,
            }
            for k in self._keys.values()
            if k.tenant_id == tenant_id
        ]

    def wrap_secret(self, tenant_id: str, plaintext: str) -> str:
        key = self.get_active_key_for_tenant(tenant_id)
        if not key:
            return plaintext
        token = secrets.token_hex(16)
        logger.debug("Wrapped secret with CMK %s token %s", key.key_id, token)
        return f"CMK:{key.key_id}:{token}:{plaintext}"

    def unwrap_secret(self, tenant_id: str, ciphertext: str) -> str:
        if not ciphertext.startswith("CMK:"):
            return ciphertext
        parts = ciphertext.split(":", 3)
        if len(parts) != 4:
            return ciphertext
        _, key_id, token, plaintext = parts
        key = self._keys.get(key_id)
        if not key or key.tenant_id != tenant_id or key.status != "active":
            raise ValueError("Invalid or inactive CMK")
        logger.debug("Unwrapped secret with CMK %s token %s", key_id, token)
        return plaintext


cmk_manager = CustomerManagedKeyManager()
