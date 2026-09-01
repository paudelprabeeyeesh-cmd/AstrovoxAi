"""Privacy & Trust — encryption, data residency, privacy dashboard."""

import time
import logging
import hashlib
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class DataEncryptor:
    """Encrypt sensitive data."""

    def __init__(self, key: str = ""):
        self._key = key or hashlib.sha256(b"astrovox-default-key").hexdigest()

    def encrypt(self, data: str) -> str:
        """Simple XOR encryption (use proper encryption in production)."""
        key_bytes = self._key.encode()
        data_bytes = data.encode()
        encrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes)])
        return encrypted.hex()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt data."""
        key_bytes = self._key.encode()
        encrypted_bytes = bytes.fromhex(encrypted)
        decrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_bytes)])
        return decrypted.decode()


class PrivacyManager:
    """Manage user privacy."""

    def __init__(self):
        self._consents: dict = {}
        self._data_residency: dict = {}

    def record_consent(self, user_id: str, consent_type: str, granted: bool):
        """Record user consent."""
        if user_id not in self._consents:
            self._consents[user_id] = {}
        self._consents[user_id][consent_type] = {
            "granted": granted,
            "timestamp": time.time(),
        }

    def has_consent(self, user_id: str, consent_type: str) -> bool:
        consents = self._consents.get(user_id, {})
        return consents.get(consent_type, {}).get("granted", False)

    def set_data_residency(self, user_id: str, region: str):
        self._data_residency[user_id] = region

    def get_data_residency(self, user_id: str) -> Optional[str]:
        return self._data_residency.get(user_id)


data_encryptor = DataEncryptor()
privacy_manager = PrivacyManager()
