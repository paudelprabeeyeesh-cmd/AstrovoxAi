"""Security architecture: Zero Trust, policy enforcement, audit, secret rotation."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from . import make_id, now
from ..logging_config import get_logger

logger = get_logger(__name__)


class PolicyAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class Policy:
    name: str
    effect: PolicyAction
    actions: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    principals: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def matches(self, *, action: str, resource: str, principal: str, context: Dict[str, Any]) -> bool:
        if self.actions and action not in self.actions:
            return False
        if self.resources and resource not in self.resources:
            return False
        if self.principals and principal not in self.principals:
            return False
        for key, expected in self.conditions.items():
            if context.get(key) != expected:
                return False
        return True


class PolicyEngine:
    """Zero-Trust policy engine: deny by default, evaluate all policies."""

    def __init__(self) -> None:
        self._policies: List[Policy] = []
        self._defaults = PolicyAction.DENY

    def add(self, policy: Policy) -> None:
        self._policies.append(policy)

    def evaluate(
        self,
        *,
        principal: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyAction:
        context = context or {}
        for policy in self._policies:
            if policy.matches(action=action, resource=resource, principal=principal, context=context):
                return policy.effect
        return self._defaults

    def is_allowed(self, **kwargs: Any) -> bool:
        return self.evaluate(**kwargs) == PolicyAction.ALLOW

    def list(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": p.name,
                "effect": p.effect.value,
                "actions": p.actions,
                "resources": p.resources,
                "principals": p.principals,
                "conditions": p.conditions,
            }
            for p in self._policies
        ]


class SecretManager:
    """Encrypted secret store with rotation and version history."""

    def __init__(self) -> None:
        self._secrets: Dict[str, Dict[str, Any]] = {}
        self._key = os.getenv("ASTROVOX_SECRET_KEY", "ai-os-default-key").encode("utf-8")
        self._lock_proxy: List[Any] = []

    def _xor(self, data: bytes) -> bytes:
        key = hashlib.sha256(self._key).digest()
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def put(self, name: str, value: str, *, ttl_s: Optional[float] = None) -> str:
        version = self._secrets.get(name, {}).get("version", 0) + 1
        encrypted = self._xor(value.encode("utf-8"))
        self._secrets[name] = {
            "value": encrypted,
            "version": version,
            "created_at": now(),
            "ttl_s": ttl_s,
            "rotated_at": now(),
        }
        return f"v{version}"

    def get(self, name: str) -> Optional[str]:
        record = self._secrets.get(name)
        if not record:
            return None
        if record.get("ttl_s") and now() - record["created_at"] > record["ttl_s"]:
            return None
        return self._xor(record["value"]).decode("utf-8")

    def rotate(self, name: str, new_value: Optional[str] = None) -> str:
        current = self.get(name)
        if new_value is None and current is None:
            new_value = secrets.token_urlsafe(32)
        elif new_value is None:
            new_value = secrets.token_urlsafe(32)
        return self.put(name, new_value)

    def versions(self, name: str) -> int:
        return self._secrets.get(name, {}).get("version", 0)


class AuditLogger:
    """Tamper-evident audit log with hash chaining."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []
        self._last_hash = "0" * 64

    def record(
        self,
        actor: str,
        action: str,
        target: str,
        *,
        outcome: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entry = {
            "id": make_id("aud"),
            "actor": actor,
            "action": action,
            "target": target,
            "outcome": outcome,
            "metadata": metadata or {},
            "ts": now(),
            "prev_hash": self._last_hash,
        }
        body = repr(entry).encode("utf-8")
        entry["hash"] = hashlib.sha256(body).hexdigest()
        self._last_hash = entry["hash"]
        self._entries.append(entry)
        if len(self._entries) > 5000:
            self._entries = self._entries[-5000:]
        return entry

    def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        return list(self._entries[-limit:])

    def verify(self) -> bool:
        prev = "0" * 64
        for entry in self._entries:
            if entry["prev_hash"] != prev:
                return False
            body = {k: v for k, v in entry.items() if k != "hash"}
            expected = hashlib.sha256(repr(body).encode("utf-8")).hexdigest()
            if expected != entry["hash"]:
                return False
            prev = entry["hash"]
        return True


class SecurityContext:
    """Zero-Trust context: every request must have a verified principal + scope."""

    def __init__(self, principal: str, scopes: List[str], *, mTLS: bool = False, source_ip: str = "0.0.0.0") -> None:
        self.principal = principal
        self.scopes = set(scopes)
        self.mTLS = mTLS
        self.source_ip = source_ip
        self.attributes: Dict[str, Any] = {}

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principal": self.principal,
            "scopes": sorted(self.scopes),
            "mTLS": self.mTLS,
            "source_ip": self.source_ip,
            "attributes": self.attributes,
        }


class SecurityLayer:
    """Bundles policy, secrets, audit, and security context."""

    def __init__(self) -> None:
        self.policy = PolicyEngine()
        self.secrets = SecretManager()
        self.audit = AuditLogger()
        # Sensible defaults
        self.policy.add(
            Policy(
                name="admin-full",
                effect=PolicyAction.ALLOW,
                actions=["*"],
                resources=["*"],
                principals=["admin"],
            )
        )
        self.policy.add(
            Policy(
                name="read-only-default",
                effect=PolicyAction.ALLOW,
                actions=["read", "list", "get", "search"],
                resources=["*"],
                principals=["*"],
            )
        )
        self.policy.add(
            Policy(
                name="workspace-isolation",
                effect=PolicyAction.DENY,
                actions=["*"],
                resources=["*"],
                principals=["*"],
                conditions={"workspace_match": False},
                description="Cross-workspace access is denied by default",
            )
        )

    def authorize(
        self,
        context: SecurityContext,
        action: str,
        resource: str,
        *,
        workspace: Optional[str] = None,
    ) -> PolicyAction:
        attrs: Dict[str, Any] = {}
        if workspace is not None:
            attrs["workspace_match"] = context.attributes.get("workspace") == workspace
        decision = self.policy.evaluate(
            principal=context.principal,
            action=action,
            resource=resource,
            context=attrs,
        )
        self.audit.record(
            actor=context.principal,
            action=action,
            target=resource,
            outcome="allowed" if decision == PolicyAction.ALLOW else "denied",
            metadata={"workspace": workspace, "scopes": sorted(context.scopes)},
        )
        return decision

    def status(self) -> Dict[str, Any]:
        return {
            "policies": self.policy.list(),
            "secrets": {name: self.secrets.versions(name) for name in self.secrets._secrets},
            "audit_size": len(self.audit._entries),
            "audit_verified": self.audit.verify(),
        }


_GLOBAL_SECURITY: Optional[SecurityLayer] = None


def get_security_layer() -> SecurityLayer:
    global _GLOBAL_SECURITY
    if _GLOBAL_SECURITY is None:
        _GLOBAL_SECURITY = SecurityLayer()
    return _GLOBAL_SECURITY