"""User authentication flow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AuthResult:
    """Authentication result."""
    success: bool
    user_id: str = ""
    token: str = ""
    error: str = ""


class Authentication:
    """User authentication flow."""

    def __init__(self, users: dict[str, str] | None = None):
        self.users = users or {}
        self.sessions: dict[str, str] = {}
        self._counter = 0

    def register(self, email: str, password: str) -> bool:
        if email in self.users:
            return False
        self.users[email] = password
        return True

    def login(self, email: str, password: str) -> AuthResult:
        if email not in self.users or self.users[email] != password:
            return AuthResult(success=False, error="invalid credentials")
        self._counter += 1
        token = f"token_{self._counter}_{email}"
        self.sessions[token] = email
        return AuthResult(success=True, user_id=email, token=token)

    def logout(self, token: str) -> bool:
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False

    def validate(self, token: str) -> str | None:
        return self.sessions.get(token)

    def verify_password(self, email: str, password: str) -> bool:
        return self.users.get(email) == password
