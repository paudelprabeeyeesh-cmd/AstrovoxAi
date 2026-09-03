"""Ecosystem monitoring, analytics, security, and audit."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Set


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------


@dataclass
class Event:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EcosystemMonitor:
    """Lightweight in-memory metrics aggregator."""

    def __init__(self, retention: int = 5000) -> None:
        self._events: Deque[Event] = deque(maxlen=retention)
        self._counters: Dict[str, int] = defaultdict(int)
        self._per_plugin: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._per_integration: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._per_endpoint: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._costs: Dict[str, float] = defaultdict(float)
        self._errors: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def record(
        self,
        name: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        plugin_id: Optional[str] = None,
        integration: Optional[str] = None,
        endpoint: Optional[str] = None,
        cost: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        payload = dict(payload or {})
        if error is not None and "error" not in payload:
            payload["error"] = error
        with self._lock:
            self._events.append(Event(name=name, payload=payload))
            self._counters[name] += 1
            if plugin_id:
                self._per_plugin[plugin_id][name] += 1
            if integration:
                self._per_integration[integration][name] += 1
            if endpoint:
                self._per_endpoint[endpoint][name] += 1
            if cost:
                self._costs[name] += cost
            if payload.get("error"):
                self._errors[str(payload["error"])] += 1

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_events": len(self._events),
                "event_counts": dict(self._counters),
                "plugins": {k: dict(v) for k, v in self._per_plugin.items()},
                "integrations": {k: dict(v) for k, v in self._per_integration.items()},
                "endpoints": {k: dict(v) for k, v in self._per_endpoint.items()},
                "costs": {k: round(v, 4) for k, v in self._costs.items()},
                "errors": dict(self._errors),
            }

    def adoption(self) -> Dict[str, Any]:
        with self._lock:
            plugins_active = {
                pid: sum(counts.values())
                for pid, counts in self._per_plugin.items()
            }
            integrations_active = {
                integration: sum(counts.values())
                for integration, counts in self._per_integration.items()
            }
        return {
            "plugins": sorted(plugins_active.items(), key=lambda kv: -kv[1]),
            "integrations": sorted(integrations_active.items(), key=lambda kv: -kv[1]),
        }

    def health(self) -> Dict[str, Any]:
        with self._lock:
            total_errors = sum(self._errors.values())
            total_events = sum(self._counters.values())
        error_rate = (total_errors / total_events) if total_events else 0.0
        status = "healthy"
        if error_rate > 0.1:
            status = "degraded"
        if error_rate > 0.25:
            status = "critical"
        return {
            "status": status,
            "error_rate": round(error_rate, 4),
            "events": total_events,
            "errors": total_errors,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {"name": e.name, "payload": e.payload, "timestamp": e.timestamp}
                for e in list(self._events)[-limit:]
            ]


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


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
    def __init__(self, path: Optional[str] = None) -> None:
        import json
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
            import json
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_dict(), default=str) + "\n")
        except Exception:
            pass
        return entry

    def tail(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return [e.to_dict() for e in self._entries[-limit:]]
        try:
            import json
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


from pathlib import Path  # noqa: E402


# ---------------------------------------------------------------------------
# Secret vault
# ---------------------------------------------------------------------------


class SecretVault:
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
        except ImportError:
            return base64.urlsafe_b64encode(value.encode()).decode()
        nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, value.encode(), None)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode()

    def decrypt(self, value: str) -> str:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            return base64.urlsafe_b64decode(value.encode()).decode()
        raw = base64.urlsafe_b64decode(value.encode())
        nonce, ciphertext = raw[:12], raw[12:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode()


import base64  # noqa: E402


# ---------------------------------------------------------------------------
# Dependency scanner
# ---------------------------------------------------------------------------


class DependencyScanner:
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

    def scan_requirements(self, requirements_text: str) -> List[Dict[str, str]]:
        findings: List[Dict[str, str]] = []
        for raw in requirements_text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[<>=!\[]", line, 1)[0].strip().lower()
            if name in self.SUSPICIOUS_PACKAGES:
                findings.append(
                    {
                        "name": name,
                        "severity": "high",
                        "description": self.SUSPICIOUS_PACKAGES[name],
                        "recommendation": "Provide an explicit allow-list for risky modules.",
                    }
                )
        return findings

    def scan_source(self, source: str) -> List[Dict[str, str]]:
        findings: List[Dict[str, str]] = []
        for bad in self.FORBIDDEN_MODULES:
            if bad in source:
                findings.append(
                    {
                        "name": bad,
                        "severity": "critical",
                        "description": f"Use of forbidden API '{bad}'.",
                        "recommendation": "Remove and replace with a safe alternative.",
                    }
                )
        if "eval(" in source or "exec(" in source:
            findings.append(
                {
                    "name": "eval/exec",
                    "severity": "high",
                    "description": "Use of eval() or exec() can lead to arbitrary code execution.",
                    "recommendation": "Use a safer alternative.",
                }
            )
        return findings


# ---------------------------------------------------------------------------
# Secret scrubber
# ---------------------------------------------------------------------------


class SecretScrubber:
    PATTERNS = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"ghp_[A-Za-z0-9]{30,}"),
        re.compile(r"xoxb-[0-9A-Za-z-]{10,}"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ]

    @classmethod
    def scrub(cls, payload: Any) -> Any:
        import json
        text = json.dumps(payload, default=str)
        for pattern in cls.PATTERNS:
            text = pattern.sub("***REDACTED***", text)
        return json.loads(text)


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------


_GLOBAL_MONITOR: Optional[EcosystemMonitor] = None
_GLOBAL_AUDIT: Optional[AuditLog] = None
_GLOBAL_VAULT: Optional[SecretVault] = None
_GLOBAL_SCANNER: Optional[DependencyScanner] = None


def get_ecosystem_monitor() -> EcosystemMonitor:
    global _GLOBAL_MONITOR
    if _GLOBAL_MONITOR is None:
        _GLOBAL_MONITOR = EcosystemMonitor()
    return _GLOBAL_MONITOR


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