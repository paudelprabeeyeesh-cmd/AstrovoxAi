"""Tenant-scoped encryption."""

import os
import base64
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .tenancy import tenant_manager

logger = logging.getLogger(__name__)


@dataclass
class TenantEncryptionKey:
    tenant_id: str
    key_id: str
    key_material: bytes
    created_at: float
    is_active: bool = True


class TenantEncryptionManager:
    def __init__(self):
        self._keys: Dict[str, TenantEncryptionKey] = {}
        self._master_key = os.getenv("TENANT_MASTER_KEY", "").encode()
        if not self._master_key:
            logger.warning("TENANT_MASTER_KEY not set; generating ephemeral master key")

    def _derive_key(self, tenant_id: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self._master_key + tenant_id.encode()))

    def get_or_create_key(self, tenant_id: str) -> TenantEncryptionKey:
        if tenant_id in self._keys:
            key = self._keys[tenant_id]
            if key.is_active:
                return key
        import time
        salt = tenant_id.encode()[:16].ljust(16, b"0")
        key_material = self._derive_key(tenant_id, salt)
        key = TenantEncryptionKey(
            tenant_id=tenant_id,
            key_id=f"{tenant_id}_key_v1",
            key_material=key_material,
            created_at=time.time(),
        )
        self._keys[tenant_id] = key
        tenant = tenant_manager.get_tenant(tenant_id)
        if tenant:
            tenant.encryption_key_id = key.key_id
        return key

    def encrypt(self, tenant_id: str, plaintext: str) -> str:
        key = self.get_or_create_key(tenant_id)
        f = Fernet(key.key_material)
        return f.encrypt(plaintext.encode()).decode()

    def decrypt(self, tenant_id: str, ciphertext: str) -> str:
        key = self.get_or_create_key(tenant_id)
        f = Fernet(key.key_material)
        return f.decrypt(ciphertext.encode()).decode()

    def rotate_key(self, tenant_id: str) -> Optional[TenantEncryptionKey]:
        old_key = self._keys.get(tenant_id)
        if old_key:
            old_key.is_active = False
        return self.get_or_create_key(tenant_id)

    def get_key_info(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        key = self._keys.get(tenant_id)
        if not key:
            return None
        return {
            "tenant_id": key.tenant_id,
            "key_id": key.key_id,
            "is_active": key.is_active,
            "created_at": key.created_at,
        }


tenant_encryption = TenantEncryptionManager()
