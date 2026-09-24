import time
import hmac
import hashlib
import base64
import json
import threading
import secrets
from dataclasses import dataclass, field
from typing import Optional, Dict, Set
from enum import Enum


class KeyStatus(Enum):
    ACTIVE = "active"
    ROTATING = "rotating"
    REVOKED = "revoked"


@dataclass
class TokenPayload:
    sub: str
    exp: float
    iat: float
    scopes: Set[str] = field(default_factory=set)
    iss: str = ""
    jti: str = ""


@dataclass
class KeyRecord:
    key_id: str
    secret: str
    algorithm: str = "HS256"
    status: KeyStatus = KeyStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    rotated_at: Optional[float] = None


class KeyRotationManager:
    def __init__(self, rotation_interval: float = 3600.0, overlap_grace: float = 600.0):
        self._keys: Dict[str, KeyRecord] = {}
        self._rotation_interval = rotation_interval
        self._overlap_grace = overlap_grace
        self._lock = threading.Lock()
        self._generate_initial_key()

    def _generate_initial_key(self):
        key_id = secrets.token_hex(8)
        secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        self._keys[key_id] = KeyRecord(key_id=key_id, secret=secret)
        self._active_key_id = key_id

    def get_active_key(self) -> KeyRecord:
        with self._lock:
            self._maybe_rotate()
            return self._keys[self._active_key_id]

    def get_key(self, key_id: str) -> Optional[KeyRecord]:
        with self._lock:
            record = self._keys.get(key_id)
            if record and record.status != KeyStatus.REVOKED:
                return record
            return None

    def rotate_keys(self) -> str:
        with self._lock:
            new_key_id = secrets.token_hex(8)
            new_secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            self._keys[new_key_id] = KeyRecord(
                key_id=new_key_id,
                secret=new_secret,
            )
            old_key_id = self._active_key_id
            self._keys[old_key_id].status = KeyStatus.ROTATING
            self._keys[old_key_id].rotated_at = time.time()
            self._active_key_id = new_key_id

            def _revoke_old():
                time.sleep(self._overlap_grace)
                with self._lock:
                    if old_key_id in self._keys:
                        self._keys[old_key_id].status = KeyStatus.REVOKED

            t = threading.Thread(target=_revoke_old, daemon=True)
            t.start()
            return new_key_id

    def _maybe_rotate(self):
        active = self._keys.get(self._active_key_id)
        if active and (time.time() - active.created_at) >= self._rotation_interval:
            self.rotate_keys()

    @property
    def active_key_id(self) -> str:
        with self._lock:
            return self._active_key_id


class JWTValidator:
    def __init__(
        self,
        rotation_manager: Optional[KeyRotationManager] = None,
        default_issuer: str = "astrovox",
        leeway: float = 30.0,
    ):
        self._rotation_manager = rotation_manager or KeyRotationManager()
        self._default_issuer = default_issuer
        self._leeway = leeway
        self._revoked_jtis: Set[str] = set()
        self._lock = threading.Lock()

    def _base64url_decode(self, data: str) -> bytes:
        padding = 4 - len(data) % 4
        data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def _sign(self, payload_segment: str, secret: str, algorithm: str = "HS256") -> str:
        if algorithm == "HS256":
            sig = hmac.new(
                secret.encode(), payload_segment.encode(), hashlib.sha256
            ).digest()
            return base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    def create_token(
        self,
        subject: str,
        scopes: Set[str],
        issuer: str = "",
        ttl: float = 3600.0,
        jti: str = "",
    ) -> tuple[str, str]:
        key = self._rotation_manager.get_active_key()
        now = time.time()
        payload = TokenPayload(
            sub=subject,
            exp=now + ttl,
            iat=now,
            scopes=scopes,
            iss=issuer or self._default_issuer,
            jti=jti or secrets.token_hex(8),
        )
        header = {"alg": key.algorithm, "kid": key.key_id, "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(
                {
                    "sub": payload.sub,
                    "exp": payload.exp,
                    "iat": payload.iat,
                    "scope": " ".join(sorted(payload.scopes)),
                    "iss": payload.iss,
                    "jti": payload.jti,
                }
            ).encode()
        ).rstrip(b"=").decode()
        signing_input = f"{header_b64}.{payload_b64}"
        signature = self._sign(signing_input, key.secret, key.algorithm)
        token = f"{signing_input}.{signature}"
        return token, key.key_id

    def validate_token(self, token: str, required_scopes: Set[str] = None) -> TokenPayload:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format: expected 3 segments")

        header_b64, payload_b64, signature_b64 = parts
        header = json.loads(self._base64url_decode(header_b64))
        kid = header.get("kid")
        alg = header.get("alg", "HS256")

        key = self._rotation_manager.get_key(kid)
        if key is None:
            raise ValueError(f"Unknown or revoked key ID: {kid}")

        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = self._sign(signing_input, key.secret, alg)
        if not hmac.compare_digest(signature_b64, expected_sig):
            raise ValueError("Invalid token signature")

        payload_data = json.loads(self._base64url_decode(payload_b64))
        now = time.time()
        exp = payload_data.get("exp", 0)
        if now > exp + self._leeway:
            raise ValueError(f"Token expired at {exp}")

        jti = payload_data.get("jti", "")
        with self._lock:
            if jti in self._revoked_jtis:
                raise ValueError("Token has been revoked")

        scope_str = payload_data.get("scope", "")
        scopes = set(scope_str.split()) if scope_str else set()

        if required_scopes:
            missing = required_scopes - scopes
            if missing:
                raise ValueError(f"Missing required scopes: {missing}")

        return TokenPayload(
            sub=payload_data.get("sub", ""),
            exp=exp,
            iat=payload_data.get("iat", 0),
            scopes=scopes,
            iss=payload_data.get("iss", ""),
            jti=jti,
        )

    def revoke_token(self, jti: str):
        with self._lock:
            self._revoked_jtis.add(jti)

    @property
    def active_key_id(self) -> str:
        return self._rotation_manager.active_key_id
