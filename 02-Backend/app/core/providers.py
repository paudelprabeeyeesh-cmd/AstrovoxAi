import logging
import os
import time
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Provider:
    name: str
    base_url: str
    env_key: str
    default_model: str
    priority: int


PROVIDERS: list[Provider] = [
    Provider(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        env_key="GROQ_API_KEY",
        default_model="llama-3.3-70b-versatile",
        priority=1,
    ),
    Provider(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        env_key="GEMINI_API_KEY",
        default_model="gemini-2.5-flash",
        priority=2,
    ),
    Provider(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
        env_key="MISTRAL_API_KEY",
        default_model="mistral-small-latest",
        priority=3,
    ),
    Provider(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        env_key="OPENROUTER_API_KEY",
        default_model="google/gemma-4-26b-a4b-it:free",
        priority=4,
    ),
    Provider(
        name="huggingface",
        base_url="https://router.huggingface.co/v1",
        env_key="HF_API_KEY",
        default_model="meta-llama/Llama-3.1-8B-Instruct",
        priority=5,
    ),
]


_active_providers_cache: Optional[list[Provider]] = None
_active_providers_ts: float = 0.0
_ACTIVE_TTL = 5.0


def get_active_providers() -> list[Provider]:
    global _active_providers_cache, _active_providers_ts
    now = time.time()
    if _active_providers_cache is not None and (now - _active_providers_ts) < _ACTIVE_TTL:
        return _active_providers_cache
    active = []
    for p in PROVIDERS:
        key = os.getenv(p.env_key)
        if key:
            active.append(p)
    _active_providers_cache = sorted(active, key=lambda p: p.priority)
    _active_providers_ts = now
    return list(_active_providers_cache)
