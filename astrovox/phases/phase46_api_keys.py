"""API key management and validation."""

from __future__ import annotations

import secrets
import time


class APIKeyManager:
    """Manage API keys for applications."""

    def __init__(self):
        self.keys: dict[str, dict] = {}

    def _generate(self) -> str:
        return "av_" + secrets.token_urlsafe(32)

    def create(self, name: str, permissions: list[str] | None = None,
               expires_at: float | None = None) -> str:
        """Create a new API key."""
        key = self._generate()
        self.keys[key] = {
            "name": name,
            "permissions": permissions or ["read"],
            "created": time.time(),
            "expires_at": expires_at,
            "active": True,
        }
        return key

    def revoke(self, key: str) -> bool:
        """Revoke an API key."""
        if key in self.keys:
            self.keys[key]["active"] = False
            return True
        return False

    def validate(self, key: str) -> dict | None:
        """Validate an API key."""
        k = self.keys.get(key)
        if k is None or not k.get("active"):
            return None
        if k.get("expires_at") and time.time() > k["expires_at"]:
            return None
        return {"name": k["name"], "permissions": k["permissions"]}

    def list_keys(self) -> list[dict]:
        return [{"name": v["name"], "active": v["active"],
                 "expires_at": v["expires_at"]} for v in self.keys.values()]

    def has_permission(self, key: str, permission: str) -> bool:
        k = self.validate(key)
        return k and permission in k["permissions"]

    def clear(self) -> None:
        self.keys.clear()
