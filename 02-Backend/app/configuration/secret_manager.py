"""Secret management with rotation support."""

import os
import json
import base64
from typing import Dict, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import secrets


class SecretManager:
    _secrets: Dict[str, Any] = {}
    _key: Optional[bytes] = None
    _rotation_schedule: Dict[str, datetime] = {}

    @classmethod
    def initialize(cls, master_key: Optional[str] = None) -> None:
        key = master_key or os.getenv("MASTER_KEY")
        if key:
            cls._key = cls._derive_key(key)
        else:
            cls._key = Fernet.generate_key()

    @classmethod
    def _derive_key(cls, password: str) -> bytes:
        salt = b"astrovox-ai-salt"
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        if not cls._key:
            cls.initialize()
        f = Fernet(cls._key)
        return f.encrypt(plaintext.encode()).decode()

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        if not cls._key:
            cls.initialize()
        f = Fernet(cls._key)
        return f.decrypt(ciphertext.encode()).decode()

    @classmethod
    def store(cls, name: str, value: str, rotate_after: Optional[timedelta] = None) -> None:
        cls._secrets[name] = cls.encrypt(value)
        if rotate_after:
            cls._rotation_schedule[name] = datetime.utcnow() + rotate_after

    @classmethod
    def retrieve(cls, name: str) -> Optional[str]:
        encrypted = cls._secrets.get(name)
        if encrypted:
            return cls.decrypt(encrypted)
        env_value = os.getenv(name.upper())
        return env_value

    @classmethod
    def rotate(cls, name: str, new_value: str) -> None:
        cls.store(name, new_value)

    @classmethod
    def get_rotation_schedule(cls) -> Dict[str, datetime]:
        return cls._rotation_schedule.copy()


SecretManager.initialize()
