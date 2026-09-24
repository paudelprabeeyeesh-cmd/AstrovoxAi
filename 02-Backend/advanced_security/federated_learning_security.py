import hashlib
import hmac
import json
import math
import os
import struct
from typing import Any, Dict, List, Optional, Tuple


class SecureAggregator:
    def __init__(self, key: Optional[str] = None) -> None:
        self._key = (key or hashlib.sha256(os.urandom(64)).hexdigest()).encode()
        self._macs: List[bytes] = []

    def _mac(self, payload: bytes) -> bytes:
        return hmac.new(self._key, payload, hashlib.sha256).digest()

    def mask(self, payload: Dict[str, Any], nonce: Optional[bytes] = None) -> bytes:
        nonce = nonce or os.urandom(32)
        payload["nonce"] = nonce.hex()
        raw = json.dumps(payload).encode()
        mac = self._mac(raw)
        self._macs.append(mac)
        return mac + raw

    def verify(self, masked: bytes) -> Tuple[bool, Dict[str, Any]]:
        mac, raw = masked[:32], masked[32:]
        expected = self._mac(raw)
        if not hmac.compare_digest(expected, mac):
            return False, {}
        return True, json.loads(raw)


class GradientMasker:
    def __init__(self, key: Optional[str] = None) -> None:
        self._key = key or hashlib.sha256(os.urandom(64)).hexdigest()

    def mask_gradient(self, gradient: List[float], nonce: Optional[str] = None) -> Tuple[List[float], str]:
        nonce = nonce or hashlib.sha256(os.urandom(32)).hexdigest()
        mask = self._keyed_mask(nonce, len(gradient))
        return [g + m for g, m in zip(gradient, mask)], nonce

    def unmask_gradient(self, gradient: List[float], nonce: str) -> List[float]:
        mask = self._keyed_mask(nonce, len(gradient))
        return [g - m for g, m in zip(gradient, mask)]

    def _keyed_mask(self, nonce: str, length: int) -> List[float]:
        seed = int(hashlib.sha256((self._key + nonce).encode()).hexdigest()[:16], 16)
        mask = []
        for _ in range(length):
            seed = (seed * 6364136223846793005 + 1) & 0xFFFFFFFFFFFFFFFF
            mask.append((seed >> 32) / 2147483648.0)
        return mask


class FederatedLossyCompression:
    @staticmethod
    def topk(values: List[float], k: int) -> Tuple[List[Tuple[int, float]], int]:
        if k <= 0:
            raise ValueError("k must be positive")
        indexed = [(i, v) for i, v in enumerate(values)]
        indexed.sort(key=lambda iv: abs(iv[1]), reverse=True)
        return indexed[:k], len(values) - k

    @staticmethod
    def reconstruct(topk: List[Tuple[int, float]], total_length: int, default: float = 0.0) -> List[float]:
        result = [default] * total_length
        for i, v in topk:
            if 0 <= i < total_length:
                result[i] = v
        return result
