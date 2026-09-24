import time
import threading
from typing import Dict, Optional, Callable, List, Set
from dataclasses import dataclass
from enum import Enum
from .oauth_jwt_validation import JWTValidator, TokenPayload


class AuthStatus(Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    UNAUTHORIZED = "unauthorized"


@dataclass
class AuthResult:
    status: AuthStatus
    reason: str
    payload: Optional[TokenPayload] = None


class AuthMiddleware:
    def __init__(
        self,
        jwt_validator: JWTValidator,
        excluded_paths: Optional[List[str]] = None,
        default_scopes: Optional[List[str]] = None,
    ):
        self._jwt_validator = jwt_validator
        self._excluded_paths = set(excluded_paths or [])
        self._default_scopes = set(default_scopes or [])
        self._stats: Dict[str, int] = {
            "allowed": 0,
            "denied": 0,
            "unauthorized": 0,
        }
        self._lock = threading.Lock()

    def process(self, path: str, method: str, token: Optional[str]) -> AuthResult:
        if path in self._excluded_paths:
            return AuthResult(status=AuthStatus.ALLOWED, reason="excluded_path")
        if not token:
            with self._lock:
                self._stats["unauthorized"] += 1
            return AuthResult(status=AuthStatus.UNAUTHORIZED, reason="missing_token")
        try:
            payload = self._jwt_validator.validate_token(token, required_scopes=self._default_scopes or None)
            with self._lock:
                self._stats["allowed"] += 1
            return AuthResult(status=AuthStatus.ALLOWED, reason="valid_token", payload=payload)
        except ValueError as exc:
            with self._lock:
                self._stats["denied"] += 1
            return AuthResult(status=AuthStatus.DENIED, reason=str(exc))

    def extract_token(self, auth_header: Optional[str]) -> Optional[str]:
        if not auth_header:
            return None
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return None

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._stats)

    def reset_stats(self):
        with self._lock:
            self._stats = {"allowed": 0, "denied": 0, "unauthorized": 0}
