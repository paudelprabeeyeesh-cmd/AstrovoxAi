"""Encryption service with key rotation and field-level encryption."""
import os
import hashlib
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken


class EncryptionService:
    def __init__(self, key: Optional[str] = None):
        key = key or os.getenv("ASTROVOX_ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key().decode()
            os.environ.setdefault("ASTROVOX_ENCRYPTION_KEY", key)
        if isinstance(key, str):
            key = key.encode()
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()

    def hash_data(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    def rotate_key(self) -> str:
        new_key = Fernet.generate_key().decode()
        self.__init__(key=new_key)
        return new_key


class FieldLevelEncryption:
    SENSITIVE_FIELDS = {"password", "secret", "token", "api_key", "credit_card", "ssn", "private_key"}

    def __init__(self, service: Optional[EncryptionService] = None):
        self._service = service or EncryptionService()

    def encrypt_dict(self, data: dict) -> dict:
        result = {}
        for key, value in data.items():
            if key.lower() in self.SENSITIVE_FIELDS and isinstance(value, str):
                result[key] = self._service.encrypt(value)
            elif isinstance(value, dict):
                result[key] = self.encrypt_dict(value)
            elif isinstance(value, list):
                result[key] = [self.encrypt_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                result[key] = value
        return result

    def decrypt_dict(self, data: dict) -> dict:
        result = {}
        for key, value in data.items():
            if key.lower() in self.SENSITIVE_FIELDS and isinstance(value, str):
                try:
                    result[key] = self._service.decrypt(value)
                except (InvalidToken, Exception):
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.decrypt_dict(value)
            elif isinstance(value, list):
                result[key] = [self.decrypt_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                result[key] = value
        return result


encryption_service = EncryptionService()
field_encryption = FieldLevelEncryption(encryption_service)
