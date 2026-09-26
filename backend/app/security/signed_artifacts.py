"""Signed artifacts verification with key management and audit trail."""
import hashlib
import hmac
import logging
import os
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class SignatureStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


@dataclass
class SignedArtifact:
    artifact_id: str
    content_hash: str
    signature: str
    algorithm: str
    public_key_id: str
    signed_at: float
    expires_at: Optional[float]
    signer: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SignedArtifactRegistry:
    def __init__(self, secret_key: Optional[str] = None):
        self._secret_key = secret_key or os.getenv("ASTROVOX_ARTIFACT_SECRET", "change-me")
        self._artifacts: Dict[str, SignedArtifact] = {}
        self._public_keys: Dict[str, str] = {}
        self._lock = __import__('threading').Lock()
        self._algorithm = "sha256"

    def sign(self, artifact_id: str, content: bytes, signer: str, ttl: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> SignedArtifact:
        content_hash = hashlib.sha256(content).hexdigest()
        sig = hmac.new(self._secret_key.encode(), content_hash.encode(), hashlib.sha256).hexdigest()
        now = time.time()
        artifact = SignedArtifact(
            artifact_id=artifact_id, content_hash=content_hash, signature=sig, algorithm=self._algorithm,
            public_key_id="default", signed_at=now, expires_at=now + ttl if ttl else None, signer=signer, metadata=metadata or {},
        )
        with self._lock:
            self._artifacts[artifact_id] = artifact
        logger.info("Signed artifact %s by %s", artifact_id, signer)
        return artifact

    def verify(self, artifact_id: str, content: bytes) -> SignatureStatus:
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return SignatureStatus.UNKNOWN
        if artifact.expires_at and time.time() > artifact.expires_at:
            return SignatureStatus.EXPIRED
        content_hash = hashlib.sha256(content).hexdigest()
        expected_sig = hmac.new(self._secret_key.encode(), content_hash.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(artifact.signature, expected_sig) and artifact.content_hash == content_hash:
            return SignatureStatus.VALID
        return SignatureStatus.INVALID

    def get_artifact(self, artifact_id: str) -> Optional[SignedArtifact]:
        with self._lock:
            return self._artifacts.get(artifact_id)

    def list_artifacts(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"artifact_id": a.artifact_id, "signer": a.signer, "signed_at": a.signed_at, "expires_at": a.expires_at} for a in self._artifacts.values()]


signed_artifact_registry = SignedArtifactRegistry()
