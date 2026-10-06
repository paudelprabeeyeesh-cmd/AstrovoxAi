"""JWT-based user authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field


@dataclass
class User:
    """A user account."""
    id: str
    email: str
    password_hash: str
    created: float = field(default_factory=lambda: time.time())
    roles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "email": self.email, "roles": self.roles,
                "created": self.created}


class AuthService:
    """JWT authentication service."""

    SECRET = "astrovox-dev-secret-change-in-prod"

    def __init__(self, users: dict[str, User] | None = None):
        self.users = users or {}
        self.tokens: dict[str, dict] = {}

    def hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        salt = salt or hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        h = hmac.new(self.SECRET.encode(), (salt + password).encode(), hashlib.sha256).hexdigest()
        return h, salt

    def register(self, email: str, password: str, roles: list[str] = None) -> User | None:
        if email in self.users:
            return None
        h, s = self.hash_password(password)
        user = User(id=f"user_{len(self.users)}", email=email, password_hash=f"{s}:{h}",
                    roles=roles or [])
        self.users[email] = user
        return user

    def login(self, email: str, password: str) -> str | None:
        user = self.users.get(email)
        if user is None:
            return None
        stored_h, stored_s = user.password_hash.split(":")
        h, _ = self.hash_password(password, stored_s)
        if h != stored_h:
            return None
        token = self._generate_token(user)
        self.tokens[token] = user.to_dict()
        return token

    def _generate_token(self, user: User) -> str:
        payload = {"sub": user.id, "email": user.email,
                   "exp": time.time() + 3600}
        body = json.dumps(payload, sort_keys=True)
        sig = hmac.new(self.SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        return f"{base64.b64encode(body.encode()).decode()}.{sig}"

    def verify(self, token: str) -> dict | None:
        if token not in self.tokens:
            return None
        try:
            body, sig = token.rsplit(".", 1)
            expected = hmac.new(self.SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
            if sig != expected:
                return None
            payload = json.loads(base64.b64decode(body))
            if payload.get("exp", 0) < time.time():
                return None
            return self.tokens[token]
        except Exception:
            return None

    def logout(self, token: str) -> bool:
        if token in self.tokens:
            del self.tokens[token]
            return True
        return False

    def get_user(self, token: str) -> dict | None:
        return self.verify(token)
