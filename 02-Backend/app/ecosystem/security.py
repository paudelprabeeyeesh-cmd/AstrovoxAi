"""Security review helpers for the ecosystem layer.

Provides:
- permission validation against allow lists
- dependency scan heuristics
- secret encryption / decryption helpers
- audit log helpers for ecosystem events
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AuditEntry:
    id: str
    actor: str
    action: str
    target: str
    status: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actor": self.actor,
            "action": self.action,
            "target": self.target,
            "status": self.status,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class AuditLog:
    """JSON-lines audit log persisted to disk."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = Path(
            path
            or os.getenv(
                "ASTROVOX_AUDIT_LOG",
                "./storage/ecosystem/audit.jsonl",
            )
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[AuditEntry] = []

    def record(
        self,
        actor: str,
        action: str,
        target: str,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=f"aud_{uuid.uuid4().hex[:10]}",
            actor=actor,
            action=action,
            target=target,
            status=status,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        try:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_dict(), default=str) + "\n")
        except Exception as exc:
            logger.warning("Failed to persist audit entry: %s", exc)
        return entry

    def tail(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return [e.to_dict() for e in self._entries[-limit:]]
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
            return [json.loads(line) for line in lines if line.strip()]
        except Exception:
            return [e.to_dict() for e in self._entries[-limit:]]

    def filter(
        self, actor: Optional[str] = None, action: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        items = self.tail(limit=1000)
        if actor:
            items = [i for i in items if i.get("actor") == actor]
        if action:
            items = [i for i in items if i.get("action") == action]
        return items


class SecretVault:
    """Encrypts secrets at rest using Fernet-equivalent AES-GCM helpers."""

    def __init__(self, key: Optional[bytes] = None) -> None:
        if key is None:
            raw = os.getenv("ASTROVOX_VAULT_KEY")
            if raw:
                key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
            else:
                key = hashlib.sha256(b"astrovox-default-key").digest()
        if len(key) < 32:
            key = hashlib.sha256(key).digest()
        self._key = key[:32]

    def encrypt(self, value: str) -> str:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:  # pragma: no cover
            return base64.urlsafe_b64encode(value.encode()).decode()
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, value.encode(), None)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode()

    def decrypt(self, value: str) -> str:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:  # pragma: no cover
            return base64.urlsafe_b64decode(value.encode()).decode()
        raw = base64.urlsafe_b64decode(value.encode())
        nonce, ciphertext = raw[:12], raw[12:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode()


@dataclass
class DependencyFinding:
    name: str
    severity: str
    description: str
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity,
            "description": self.description,
            "recommendation": self.recommendation,
        }


class DependencyScanner:
    """Heuristic dependency scanner.

    Not a replacement for ``pip-audit``/``npm audit``, but it surfaces
    common red flags so we can block obviously risky plugins from
    being installed.
    """

    SUSPICIOUS_PACKAGES = {
        "pickle": "Pickle can execute arbitrary code on load.",
        "marshal": "Marshal can be used to load arbitrary code objects.",
        "ctypes": "ctypes grants low-level memory access.",
        "subprocess": "subprocess can shell out.",
        "socket": "Direct socket access bypasses our HTTP allowlist.",
        "requests": "Use the platform HTTP client for visibility.",
    }

    FORBIDDEN_MODULES = {
        "os.system",
        "os.popen",
        "subprocess.Popen",
        "subprocess.call",
        "code.interact",
    }

    def scan_requirements(self, requirements_text: str) -> List[DependencyFinding]:
        findings: List[DependencyFinding] = []
        for raw in requirements_text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[<>=!\[]", line, 1)[0].strip().lower()
            if name in self.SUSPICIOUS_PACKAGES:
                findings.append(
                    DependencyFinding(
                        name=name,
                        severity="high",
                        description=self.SUSPICIOUS_PACKAGES[name],
                        recommendation="Provide an explicit allow-list for risky modules.",
                    )
                )
        return findings

    def scan_source(self, source: str) -> List[DependencyFinding]:
        findings: List[DependencyFinding] = []
        for bad in self.FORBIDDEN_MODULES:
            if bad in source:
                findings.append(
                    DependencyFinding(
                        name=bad,
                        severity="critical",
                        description=f"Use of forbidden API '{bad}'.",
                        recommendation="Remove and replace with a safe alternative.",
                    )
                )
        if "eval(" in source or "exec(" in source:
            findings.append(
                DependencyFinding(
                    name="eval/exec",
                    severity="high",
                    description="Use of eval() or exec() can lead to arbitrary code execution.",
                )
            )
        return findings


def validate_permissions(
    requested: List[str],
    allowed: Optional[Set[str]] = None,
) -> List[str]:
    allowed = allowed or set()
    invalid: List[str] = []
    for p in requested:
        if not p or not isinstance(p, str):
            invalid.append(str(p))
            continue
        if allowed and p not in allowed:
            invalid.append(p)
    return invalid


class SecretScrubber:
    PATTERNS = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"ghp_[A-Za-z0-9]{30,}"),
        re.compile(r"xoxb-[0-9A-Za-z-]{10,}"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ]

    @classmethod
    def scrub(cls, payload: Any) -> Any:
        text = json.dumps(payload, default=str)
        for pattern in cls.PATTERNS:
            text = pattern.sub("***REDACTED***", text)
        return json.loads(text)


_GLOBAL_AUDIT: Optional[AuditLog] = None
_GLOBAL_VAULT: Optional[SecretVault] = None
_GLOBAL_SCANNER: Optional[DependencyScanner] = None


def get_audit_log() -> AuditLog:
    global _GLOBAL_AUDIT
    if _GLOBAL_AUDIT is None:
        _GLOBAL_AUDIT = AuditLog()
    return _GLOBAL_AUDIT


def get_secret_vault() -> SecretVault:
    global _GLOBAL_VAULT
    if _GLOBAL_VAULT is None:
        _GLOBAL_VAULT = SecretVault()
    return _GLOBAL_VAULT


def get_dependency_scanner() -> DependencyScanner:
    global _GLOBAL_SCANNER
    if _GLOBAL_SCANNER is None:
        _GLOBAL_SCANNER = DependencyScanner()
    return _GLOBAL_SCANNER