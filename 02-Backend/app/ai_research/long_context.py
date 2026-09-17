"""Long-context optimization with sliding window and compression."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ContextWindow:
    max_tokens: int = 128000
    reserve_tokens: int = 4096
    sliding_window: int = 8192

    def available(self) -> int:
        return max(0, self.max_tokens - self.reserve_tokens)

    def optimize(self, segments: list[dict]) -> list[dict]:
        allowed = self.available()
        total = sum(int(seg.get("tokens", 0)) for seg in segments)
        if total <= allowed:
            return segments
        kept: list[dict] = []
        used = 0
        for seg in reversed(segments):
            tokens = int(seg.get("tokens", 0))
            if used + tokens <= allowed:
                kept.append(seg)
                used += tokens
            else:
                break
        return list(reversed(kept))
