import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Attestation:
    enclave_id: str
    public_key: str
    measurements: Dict[str, str]
    timestamp: float = field(default_factory=time.time)


@dataclass
class SealedBlob:
    ciphertext: str
    tag: str
    nonce: str
    enclave_id: str


class SecureEnclave:
    def __init__(self, enclave_id: Optional[str] = None) -> None:
        self._enclave_id = enclave_id or hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        self._key = hashlib.sha256(self._enclave_id.encode()).digest()
        self._measurements: Dict[str, str] = {}
        self._sealed: List[SealedBlob] = []

    @property
    def enclave_id(self) -> str:
        return self._enclave_id

    def extend_measurement(self, component: str, data: bytes) -> None:
        self._measurements[component] = hashlib.sha256(data).hexdigest()

    def attest(self) -> Attestation:
        return Attestation(
            enclave_id=self._enclave_id,
            public_key=hashlib.sha256(self._key).hexdigest()[:32],
            measurements=dict(self._measurements),
        )

    def seal(self, plaintext: str, associated_data: Optional[str] = None) -> SealedBlob:
        nonce = os.urandom(16).hex()
        ad = (associated_data or "").encode()
        payload = plaintext.encode() + ad
        tag = hmac.new(self._key, (nonce.encode() + payload), hashlib.sha256).hexdigest()[:16]
        blob = SealedBlob(
            ciphertext=hashlib.sha256(payload).hexdigest(),
            tag=tag,
            nonce=nonce,
            enclave_id=self._enclave_id,
        )
        self._sealed.append(blob)
        return blob

    def unseal(self, blob: SealedBlob, associated_data: Optional[str] = None) -> str:
        if blob.enclave_id != self._enclave_id:
            raise ValueError("Blob belongs to different enclave")
        ad = (associated_data or "").encode()
        payload = blob.ciphertext.encode() + ad
        expected_tag = hmac.new(self._key, (blob.nonce.encode() + payload), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(expected_tag, blob.tag):
            raise ValueError("Integrity check failed")
        return hashlib.sha256(payload).hexdigest()

    def memory_guard(self, address: int, length: int, max_bound: int = 65536) -> bool:
        return 0 <= address and 0 < length and address + length <= max_bound
