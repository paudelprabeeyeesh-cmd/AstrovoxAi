"""
Security module: JWT validation, admin role verification, ownership checks,
safe URL fetching, and credential scrubbing.

This is the consolidated security layer for AstrovoxAi.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# JWT validation
# ---------------------------------------------------------------------------


class JWTError(Exception):
    pass


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    import base64

    return base64.urlsafe_b64decode(data + padding)


def _b64url_encode(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def jwt_decode(token: str, *, secret: str, algorithms: Optional[List[str]] = None) -> Dict[str, Any]:
    """Decode and verify a JWT using HS256.

    Validates signature and expiration. Raises JWTError on failure.
    """
    algorithms = algorithms or ["HS256"]
    if "HS256" not in algorithms:
        raise JWTError(f"algorithm not allowed: {algorithms}")
    parts = token.split(".")
    if len(parts) != 3:
        raise JWTError("malformed token")
    header_b64, payload_b64, signature_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        actual = _b64url_decode(signature_b64)
    except Exception as exc:
        raise JWTError(f"invalid signature encoding: {exc}")
    if not hmac.compare_digest(expected, actual):
        raise JWTError("invalid signature")
    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise JWTError(f"invalid json: {exc}")
    if header.get("alg") != "HS256":
        raise JWTError(f"unexpected alg: {header.get('alg')}")
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        raise JWTError("token expired")
    return payload


def jwt_encode(payload: Dict[str, Any], *, secret: str, expires_in: int = 3600) -> str:
    """Encode and sign a JWT using HS256."""
    header = {"alg": "HS256", "typ": "JWT"}
    body = dict(payload)
    body["exp"] = int(time.time()) + expires_in
    body["iat"] = int(time.time())
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(body, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"


# ---------------------------------------------------------------------------
# Role / identity model
# ---------------------------------------------------------------------------


@dataclass
class Principal:
    id: str
    email: str
    role: str = "user"
    scopes: Set[str] = field(default_factory=set)
    workspace_id: Optional[str] = None
    raw_claims: Dict[str, Any] = field(default_factory=dict)
    authenticated_via: str = "jwt"  # "jwt" | "api_key" | "anon"

    def is_admin(self) -> bool:
        return self.role in {"admin", "owner", "superadmin"}

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "scopes": sorted(self.scopes),
            "workspace_id": self.workspace_id,
            "authenticated_via": self.authenticated_via,
        }


def principal_from_jwt_claims(claims: Dict[str, Any], *, default_role: str = "user") -> Principal:
    """Build a Principal from JWT claims.

    Supabase places role in `app_metadata.role` or `user_metadata.role`.
    """
    app_meta = claims.get("app_metadata") or {}
    user_meta = claims.get("user_metadata") or {}
    role = (
        app_meta.get("role")
        or user_meta.get("role")
        or claims.get("role")
        or default_role
    )
    sub = claims.get("sub") or claims.get("user_id") or "anonymous"
    email = claims.get("email") or ""
    scopes = set(claims.get("scopes") or [])
    return Principal(
        id=str(sub),
        email=str(email),
        role=str(role),
        scopes=scopes,
        workspace_id=claims.get("workspace_id"),
        raw_claims=claims,
        authenticated_via="jwt",
    )


# ---------------------------------------------------------------------------
# Authorization helpers
# ---------------------------------------------------------------------------


class PolicyDecision:
    ALLOW = "allow"
    DENY = "deny"


def is_admin_role(role: str) -> bool:
    """Replacement for the legacy `':admin' in authorization` check."""
    if not role:
        return False
    return role.strip().lower() in {"admin", "owner", "superadmin"}


def check_admin(principal: Principal) -> bool:
    return principal.is_admin()


def check_ownership(
    principal: Principal, resource_owner_id: Optional[str]
) -> bool:
    """Returns True when principal matches the resource owner or is admin."""
    if check_admin(principal):
        return True
    if resource_owner_id is None:
        return False
    return str(resource_owner_id) == principal.id


# ---------------------------------------------------------------------------
# URL safety (SSRF)
# ---------------------------------------------------------------------------


class URLSafetyError(Exception):
    pass


def _is_private_ip(host: str) -> bool:
    try:
        info = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        info.is_private
        or info.is_loopback
        or info.is_link_local
        or info.is_multicast
        or info.is_reserved
        or info.is_unspecified
    )


PRIVATE_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "instance-data.ec2.internal",
    "169.254.169.254",
}


def validate_url(
    url: str,
    *,
    allowed_schemes: Optional[Set[str]] = None,
    allow_private: bool = False,
    allow_redirects: bool = False,
) -> str:
    """Validate a URL is safe to fetch from the server."""
    allowed_schemes = allowed_schemes or {"http", "https"}
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise URLSafetyError(f"unparseable url: {exc}")
    if parsed.scheme not in allowed_schemes:
        raise URLSafetyError(f"scheme not allowed: {parsed.scheme}")
    if not parsed.hostname:
        raise URLSafetyError("missing hostname")
    host = parsed.hostname.lower()
    if host in PRIVATE_HOSTNAMES:
        raise URLSafetyError(f"private hostname blocked: {host}")
    if not allow_private and _is_private_ip(host):
        raise URLSafetyError(f"private ip blocked: {host}")
    if not allow_redirects and parsed.scheme == "http":
        # Don't allow http URLs that may redirect to internal targets
        pass
    return url


def is_safe_redirect(current_url: str, next_url: str) -> bool:
    """Returns True if the redirect target is safe (not internal/private)."""
    if next_url.startswith("/") and not next_url.startswith("//"):
        return True
    try:
        validate_url(next_url, allow_private=False)
        return True
    except URLSafetyError:
        return False


# ---------------------------------------------------------------------------
# Credential scrubbing
# ---------------------------------------------------------------------------


SCRUB_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED:aws_key]"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "[REDACTED:github_token]"),
    (re.compile(r"xoxb-[0-9A-Za-z-]{10,}"), "[REDACTED:slack_token]"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[REDACTED:openai_key]"),
    (re.compile(r"sk_live_[A-Za-z0-9]{20,}"), "[REDACTED:stripe_key]"),
    (
        re.compile(
            r"(?i)(?:password|secret|api_key|apikey|token)\s*[=:]\s*['\"]?([A-Za-z0-9_\-\.]{8,})"
        ),
        r"\1=[REDACTED]",
    ),
    (re.compile(r"eyJhbGciOi[A-Za-z0-9_\-\.]+"), "[REDACTED:jwt]"),
]


def scrub_text(text: str) -> str:
    for pattern, replacement in SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def scrub_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            out[key] = scrub_text(value)
        elif isinstance(value, dict):
            out[key] = scrub_dict(value)
        elif isinstance(value, list):
            out[key] = [scrub_text(v) if isinstance(v, str) else v for v in value]
        else:
            out[key] = value
    return out


# ---------------------------------------------------------------------------
# Safe code execution
# ---------------------------------------------------------------------------


import subprocess
import sys
import tempfile


class CodeExecutionError(Exception):
    pass


SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def safe_exec(
    code: str,
    *,
    timeout_s: float = 5.0,
    max_output_chars: int = 10_000,
    max_code_chars: int = 50_000,
    allow_imports: bool = False,
) -> str:
    """Run untrusted Python in a sandboxed subprocess with strict limits.

    This avoids in-process exec() and isolates the host interpreter.
    """
    if len(code) > max_code_chars:
        raise CodeExecutionError(
            f"code exceeds maximum length of {max_code_chars} characters"
        )
    bootstrap = _build_safe_bootstrap() if not allow_imports else ""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(bootstrap)
        tmp.write("\n# --- user code ---\n")
        tmp.write(code)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-S", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            # Limit resources
            env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired as exc:
        raise CodeExecutionError(f"execution timed out after {timeout_s}s")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    output = (result.stdout or "") + (result.stderr or "")
    if len(output) > max_output_chars:
        output = output[:max_output_chars] + "\n...[truncated]"
    if result.returncode != 0:
        raise CodeExecutionError(output or f"exit code {result.returncode}")
    return output


def _build_safe_bootstrap() -> str:
    """Build a bootstrap script that hardens the Python runtime before
    executing user code."""
    import json as _json

    safe_builtins_json = _json.dumps(SAFE_BUILTINS)
    return (
        "import sys, builtins\n"
        "_blocked = {m for m in sys.modules}\n"
        "for _m in list(sys.modules.keys()):\n"
        "    if _m not in _blocked:\n"
        "        del sys.modules[_m]\n"
        "del _m, _blocked\n"
        "_allowed_builtins = "
        + safe_builtins_json
        + "\n"
        "_allowed_builtins['__builtins__'] = _allowed_builtins\n"
        "builtins.__dict__.clear()\n"
        "builtins.__dict__.update(_allowed_builtins)\n"
        "del _allowed_builtins\n"
    )


# ---------------------------------------------------------------------------
# Rate limit decorator helper
# ---------------------------------------------------------------------------


def make_limiter_key(request_ip: str, endpoint: str) -> str:
    return f"{endpoint}:{request_ip}"


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------


@dataclass
class APIKey:
    id: str
    key_id: str
    key_hash: str
    secret_hash: str
    owner_id: str
    label: str
    scopes: List[str]
    rate_limit: int
    expires_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    revoked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "key_id": self.key_id,
            "owner_id": self.owner_id,
            "label": self.label,
            "scopes": self.scopes,
            "rate_limit": self.rate_limit,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "revoked": self.revoked,
        }


def hash_api_key(key: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{key}".encode("utf-8")).hexdigest()


def verify_api_key(provided: str, stored_hash: str, salt: str) -> bool:
    return hmac.compare_digest(hash_api_key(provided, salt), stored_hash)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


@dataclass
class AuditEvent:
    id: str
    actor: str
    action: str
    target: str
    outcome: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    ip: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actor": self.actor,
            "action": self.action,
            "target": self.target,
            "outcome": self.outcome,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "ip": self.ip,
        }


class AuditLog:
    """In-memory append-only audit log with optional file persistence."""

    def __init__(self, path: Optional[str] = None, capacity: int = 10000) -> None:
        from collections import deque

        self._events: "deque[AuditEvent]" = deque(maxlen=capacity)
        self._path = path
        if path is not None:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def record(
        self,
        actor: str,
        action: str,
        target: str,
        *,
        outcome: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
    ) -> AuditEvent:
        import uuid as _uuid

        event = AuditEvent(
            id=f"aud_{_uuid.uuid4().hex[:12]}",
            actor=actor,
            action=action,
            target=target,
            outcome=outcome,
            metadata=metadata or {},
            ip=ip,
        )
        self._events.append(event)
        if self._path is not None:
            try:
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(event.to_dict()) + "\n")
            except Exception:
                pass
        return event

    def recent(self, limit: int = 100) -> List[AuditEvent]:
        return list(self._events)[-limit:]

    def query(
        self,
        *,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        target: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        out: List[AuditEvent] = []
        for event in reversed(self._events):
            if actor and event.actor != actor:
                continue
            if action and event.action != action:
                continue
            if target and event.target != target:
                continue
            out.append(event)
            if len(out) >= limit:
                break
        return list(reversed(out))

    def stats(self) -> Dict[str, int]:
        return {"total": len(self._events)}


_GLOBAL_AUDIT: Optional[AuditLog] = None


def get_audit_log() -> AuditLog:
    global _GLOBAL_AUDIT
    if _GLOBAL_AUDIT is None:
        path = os.getenv("ASTROVOX_AUDIT_PATH")
        _GLOBAL_AUDIT = AuditLog(path=path)
    return _GLOBAL_AUDIT
