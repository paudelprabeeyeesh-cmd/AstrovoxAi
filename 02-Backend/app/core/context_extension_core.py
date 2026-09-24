"""
Context window extension with memory tiers and budget management.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class MemoryTier:
    name: str
    max_tokens: int
    current_tokens: int = 0
    priority: int = 0


class ContextWindowExtension:
    """Extends context window using tiered memory."""

    def __init__(self, max_context: int = 128000):
        self.max_context = max_context
        self.tiers: List[MemoryTier] = [
            MemoryTier(name="system", max_tokens=max_context, priority=3),
            MemoryTier(name="recent_history", max_tokens=max_context // 4, priority=2),
            MemoryTier(name="long_term_memory", max_tokens=max_context // 4, priority=1),
            MemoryTier(name="compressed_memory", max_tokens=max_context // 8, priority=0),
        ]
        self.system_prompt = ""
        self.recent_history: List[dict] = []
        self.long_term_memory: List[dict] = []
        self.compressed_memory: List[str] = []

    def set_system_prompt(self, prompt: str, token_count: int = 0):
        self.system_prompt = prompt
        self.tiers[0].current_tokens = token_count

    def add_history(self, role: str, content: str, tokens: int):
        self.recent_history.append({"role": role, "content": content, "tokens": tokens})
        self.tiers[1].current_tokens += tokens
        if self.tiers[1].current_tokens > self.tiers[1].max_tokens:
            self._compress_history()

    def add_memory(self, content: str, tokens: int, importance: float = 0.5):
        if importance > 0.7:
            self.long_term_memory.append({"content": content, "tokens": tokens, "importance": importance})
            self.tiers[2].current_tokens += tokens
        else:
            self.compressed_memory.append(content)
            self.tiers[3].current_tokens += tokens

    def _compress_history(self):
        if not self.recent_history:
            return
        compressed = "\n".join(f"{h['role']}: {h['content'][:100]}" for h in self.recent_history[-10:])
        self.compressed_memory.append(compressed)
        removed = sum(h["tokens"] for h in self.recent_history)
        self.recent_history = self.recent_history[-20:]
        self.tiers[1].current_tokens = sum(h["tokens"] for h in self.recent_history)
        self.tiers[3].current_tokens += removed - self.tiers[1].current_tokens

    def calculate_budget(self) -> dict:
        total = sum(t.current_tokens for t in self.tiers)
        return {
            "total_tokens": total,
            "max_context": self.max_context,
            "remaining": self.max_context - total,
            "budget_exceeded": total > self.max_context,
            "tiers": [
                {"name": t.name, "current": t.current_tokens, "max": t.max_tokens, "priority": t.priority}
                for t in self.tiers
            ],
        }

    def truncate_to_budget(self, target_tokens: int) -> int:
        removed = 0
        while self.calculate_budget()["total_tokens"] > target_tokens:
            for tier in sorted(self.tiers, key=lambda t: t.priority):
                if tier.current_tokens > 0:
                    removed += tier.current_tokens
                    tier.current_tokens = 0
                    if tier.name == "recent_history":
                        self.recent_history = self.recent_history[-5:]
                        tier.current_tokens = sum(h["tokens"] for h in self.recent_history)
                    break
        return removed
