import os
import base64
from cryptography.fernet import Fernet

_fernet = None

def get_fernet():
    global _fernet
    if _fernet is None:
        key = os.getenv("ASTROVOX_ENCRYPTION_KEY")
        if not key:
            key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet

def encrypt(text: str) -> str:
    if not text:
        return text
    return get_fernet().encrypt(text.encode()).decode()

def decrypt(token: str) -> str:
    if not token:
        return token
    try:
        return get_fernet().decrypt(token.encode()).decode()
    except Exception:
        return token
