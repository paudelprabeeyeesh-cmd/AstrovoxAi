"""Artifact signing for release integrity."""
from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Signature:
    artifact_id: str
    signature: str
    algorithm: str
    signed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ArtifactSigner:
    def __init__(self, secret: str = "changeme"):
        self._secret = secret
        self._signatures: Dict[str, Signature] = {}

    def sign(self, artifact_id: str, data: bytes) -> Signature:
        signature = hmac.new(self._secret.encode(), data, hashlib.sha256).hexdigest()
        sig = Signature(artifact_id=artifact_id, signature=signature, algorithm="hmac-sha256")
        self._signatures[artifact_id] = sig
        return sig

    def verify(self, artifact_id: str, data: bytes) -> bool:
        sig = self._signatures.get(artifact_id)
        if not sig:
            return False
        expected = hmac.new(self._secret.encode(), data, hashlib.sha256).hexdigest()
        return sig.signature == expected


artifact_signer = ArtifactSigner()
