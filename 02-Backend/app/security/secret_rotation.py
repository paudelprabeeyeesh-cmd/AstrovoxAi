"""Secret rotation for API keys, JWT signing keys, and other credentials.

Provides:
1. API key rotation with versioning
2. JWT secret rotation with grace period
3. Database credential rotation tracking
4. Third-party token rotation (OpenAI, Stripe, etc.)
5. Rotation audit trail
6. Grace period for old secrets during rotation
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SecretType(str, Enum):
    API_KEY = "api_key"
    JWT_SECRET = "jwt_secret"
    DATABASE_PASSWORD = "database_password"
    OPENAI_KEY = "openai_key"
    STRIPE_KEY = "stripe_key"
    WEBHOOK_SECRET = "webhook_secret"
    ENCRYPTION_KEY = "encryption_key"


class SecretStatus(str, Enum):
    ACTIVE = "active"
    ROTATING = "rotating"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


@dataclass
class SecretVersion:
    secret_type: SecretType
    version: int
    value_hash: str
    status: SecretStatus = SecretStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    rotated_at: Optional[float] = None
    rotated_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RotationPolicy:
    secret_type: SecretType
    rotation_interval_days: int = 90
    grace_period_days: int = 7
    max_versions: int = 3
    alert_before_days: int = 14


@dataclass
class RotationResult:
    success: bool
    secret_type: SecretType
    new_version: int
    old_version: int
    message: str
    timestamp: float = field(default_factory=time.time)


class SecretRotationManager:
    """Manage secret rotation with versioning and grace periods."""

    def __init__(self) -> None:
        self._versions: Dict[SecretType, Dict[int, SecretVersion]] = {}
        self._policies: Dict[SecretType, RotationPolicy] = {}
        self._lock = threading.Lock()
        self._audit: List[Dict[str, Any]] = []
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = {
            SecretType.API_KEY: RotationPolicy(SecretType.API_KEY, rotation_interval_days=90, grace_period_days=7),
            SecretType.JWT_SECRET: RotationPolicy(SecretType.JWT_SECRET, rotation_interval_days=30, grace_period_days=2),
            SecretType.DATABASE_PASSWORD: RotationPolicy(SecretType.DATABASE_PASSWORD, rotation_interval_days=60, grace_period_days=7),
            SecretType.OPENAI_KEY: RotationPolicy(SecretType.OPENAI_KEY, rotation_interval_days=90, grace_period_days=7),
            SecretType.STRIPE_KEY: RotationPolicy(SecretType.STRIPE_KEY, rotation_interval_days=90, grace_period_days=7),
            SecretType.WEBHOOK_SECRET: RotationPolicy(SecretType.WEBHOOK_SECRET, rotation_interval_days=60, grace_period_days=7),
            SecretType.ENCRYPTION_KEY: RotationPolicy(SecretType.ENCRYPTION_KEY, rotation_interval_days=180, grace_period_days=30),
        }
        for secret_type, policy in defaults.items():
            self._policies[secret_type] = policy

    def _hash_secret(self, value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def register_secret(self, secret_type: SecretType, value: str, metadata: Dict[str, Any] = None) -> SecretVersion:
        with self._lock:
            versions = self._versions.setdefault(secret_type, {})
            version = max(versions.keys()) + 1 if versions else 1
            secret_version = SecretVersion(
                secret_type=secret_type,
                version=version,
                value_hash=self._hash_secret(value),
                status=SecretStatus.ACTIVE,
                metadata=metadata or {},
            )
            versions[version] = secret_version
            self._audit.append({
                "event": "register",
                "secret_type": secret_type.value,
                "version": version,
                "timestamp": time.time(),
            })
            return secret_version

    def rotate(self, secret_type: SecretType, new_value: str, rotated_by: str = "system") -> RotationResult:
        with self._lock:
            versions = self._versions.setdefault(secret_type, {})
            current_version = max((v for v in versions if versions[v].status == SecretStatus.ACTIVE), default=None)

            if current_version is None:
                return RotationResult(
                    success=False,
                    secret_type=secret_type,
                    new_version=0,
                    old_version=0,
                    message="No active secret to rotate",
                )

            old_version = current_version
            policy = self._policies.get(secret_type)
            max_versions = policy.max_versions if policy else 3

            new_version = old_version + 1
            secret_version = SecretVersion(
                secret_type=secret_type,
                version=new_version,
                value_hash=self._hash_secret(new_value),
                status=SecretStatus.ACTIVE,
                rotated_by=rotated_by,
            )
            if policy:
                secret_version.expires_at = time.time() + (policy.rotation_interval_days * 86400)

            versions[new_version] = secret_version
            versions[old_version].status = SecretStatus.DEPRECATED
            versions[old_version].rotated_at = time.time()
            versions[old_version].rotated_by = rotated_by

            self._audit.append({
                "event": "rotate",
                "secret_type": secret_type.value,
                "old_version": old_version,
                "new_version": new_version,
                "rotated_by": rotated_by,
                "timestamp": time.time(),
            })

            expired = [v for v in versions if versions[v].status == SecretStatus.REVOKED and len(versions) > max_versions]
            for v in expired:
                del versions[v]

            logger.info("Rotated %s from v%d to v%d by %s", secret_type.value, old_version, new_version, rotated_by)

            return RotationResult(
                success=True,
                secret_type=secret_type,
                new_version=new_version,
                old_version=old_version,
                message=f"Rotated to version {new_version}",
            )

    def revoke(self, secret_type: SecretType, version: int, reason: str = "manual") -> bool:
        with self._lock:
            versions = self._versions.get(secret_type, {})
            secret_version = versions.get(version)
            if not secret_version:
                return False
            if secret_version.status == SecretStatus.REVOKED:
                return True
            secret_version.status = SecretStatus.REVOKED
            secret_version.rotated_at = time.time()
            self._audit.append({
                "event": "revoke",
                "secret_type": secret_type.value,
                "version": version,
                "reason": reason,
                "timestamp": time.time(),
            })
            return True

    def get_active_version(self, secret_type: SecretType) -> Optional[int]:
        with self._lock:
            versions = self._versions.get(secret_type, {})
            for v in sorted(versions.keys(), reverse=True):
                if versions[v].status == SecretStatus.ACTIVE:
                    return v
            return None

    def get_rotation_due(self) -> List[Dict[str, Any]]:
        due: List[Dict[str, Any]] = []
        now = time.time()
        with self._lock:
            for secret_type, versions in self._versions.items():
                policy = self._policies.get(secret_type)
                if not policy:
                    continue
                for version, secret_version in versions.items():
                    if secret_version.status != SecretStatus.ACTIVE:
                        continue
                    created_days = (now - secret_version.created_at) / 86400
                    if created_days >= policy.rotation_interval_days - policy.alert_before_days:
                        due.append({
                            "secret_type": secret_type.value,
                            "version": version,
                            "age_days": round(created_days, 1),
                            "max_age_days": policy.rotation_interval_days,
                            "alert_days": policy.alert_before_days,
                        })
        return due

    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return self._audit[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            stats = {}
            for secret_type, versions in self._versions.items():
                stats[secret_type.value] = {
                    "total_versions": len(versions),
                    "active": sum(1 for v in versions.values() if v.status == SecretStatus.ACTIVE),
                    "deprecated": sum(1 for v in versions.values() if v.status == SecretStatus.DEPRECATED),
                    "revoked": sum(1 for v in versions.values() if v.status == SecretStatus.REVOKED),
                }
            return stats


secret_rotation_manager = SecretRotationManager()


def rotate_secret(secret_type: SecretType, new_value: str, rotated_by: str = "system") -> RotationResult:
    return secret_rotation_manager.rotate(secret_type, new_value, rotated_by)


def revoke_secret(secret_type: SecretType, version: int, reason: str = "manual") -> bool:
    return secret_rotation_manager.revoke(secret_type, version, reason)


def get_active_secret_version(secret_type: SecretType) -> Optional[int]:
    return secret_rotation_manager.get_active_version(secret_type)


def get_rotation_due() -> List[Dict[str, Any]]:
    return secret_rotation_manager.get_rotation_due()


def get_rotation_stats() -> Dict[str, Any]:
    return secret_rotation_manager.get_stats()
