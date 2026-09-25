"""Idempotency key utility helpers."""

from __future__ import annotations

import hashlib
import secrets
from typing import Optional


def generate_idempotency_key(seed: Optional[str] = None) -> str:
    if seed:
        return hashlib.sha256(seed.encode()).hexdigest()[:32]
    return secrets.token_hex(16)
