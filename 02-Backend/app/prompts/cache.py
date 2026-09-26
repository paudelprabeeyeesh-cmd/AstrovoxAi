"""Prompt caching for performance optimization."""

from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib


@dataclass
class CachedPrompt:
    prompt_hash: str
    prompt_id: str
    version: str
    content: str
    hit_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class PromptCache:
    _cache: Dict[str, CachedPrompt] = {}
    _hit_count: int = 0
    _miss_count: int = 0

    @classmethod
    def _compute_hash(cls, prompt_id: str, variables: Dict[str, Any]) -> str:
        raw = f"{prompt_id}:{sorted(variables.items())}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def get(cls, prompt_id: str, variables: Dict[str, Any]) -> Optional[str]:
        key = cls._compute_hash(prompt_id, variables)
        cached = cls._cache.get(key)
        if cached:
            cached.hit_count += 1
            cached.last_accessed = datetime.now(timezone.utc)
            cls._hit_count += 1
            return cached.content
        cls._miss_count += 1
        return None

    @classmethod
    def put(cls, prompt_id: str, variables: Dict[str, Any], content: str, version: str = "1.0.0") -> None:
        key = cls._compute_hash(prompt_id, variables)
        cached = CachedPrompt(
            prompt_hash=key,
            prompt_id=prompt_id,
            version=version,
            content=content,
        )
        cls._cache[key] = cached

    @classmethod
    def invalidate(cls, prompt_id: str) -> None:
        cls._cache = {k: v for k, v in cls._cache.items() if v.prompt_id != prompt_id}

    @classmethod
    def stats(cls) -> Dict[str, Any]:
        total = cls._hit_count + cls._miss_count
        hit_rate = cls._hit_count / total if total > 0 else 0.0
        return {
            "hits": cls._hit_count,
            "misses": cls._miss_count,
            "hit_rate": hit_rate,
            "size": len(cls._cache),
        }
