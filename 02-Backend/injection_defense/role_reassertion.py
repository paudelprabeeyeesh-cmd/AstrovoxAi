"""Role Re-Assertion: periodically re-inject system prompt without blowing context window."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ReAssertionConfig:
    system_prompt: str
    max_context_tokens: int
    reassert_interval: int
    compression_ratio: float = 0.25
    min_prompt_tokens: int = 50
    marker: str = "[SYSTEM_PROMPT_REASSERTED]"


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def compress_prompt(prompt: str, ratio: float) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", prompt.strip())
    if not sentences:
        return prompt
    keep = max(1, int(len(sentences) * ratio))
    return " ".join(sentences[:keep])


@dataclass
class ConversationBuffer:
    config: ReAssertionConfig
    messages: list[dict] = field(default_factory=list)
    token_count: int = 0
    reassertion_count: int = 0

    def add_message(self, role: str, content: str) -> None:
        tokens = estimate_tokens(content)
        while (self.token_count + tokens > self.config.max_context_tokens
                and len(self.messages) > 0):
            oldest = self.messages.pop()
            self.token_count -= estimate_tokens(oldest["content"])
        self.messages.append({"role": role, "content": content})
        self.token_count += tokens
        self.reassertion_count += 1
        self._maybe_reassert()

    def _maybe_reassert(self) -> None:
        interval = self.config.reassert_interval
        if interval > 0 and self.reassertion_count % interval == 0:
            self._reassert()

    def _reassert(self) -> None:
        system_prompt = self.config.system_prompt
        prompt_tokens = estimate_tokens(system_prompt)
        compressed = system_prompt
        if prompt_tokens > self.config.min_prompt_tokens:
            compressed = compress_prompt(system_prompt, self.config.compression_ratio)
        marker = self.config.marker
        content = f"{marker}\n{compressed}"
        self.messages.insert(0, {"role": "system", "content": content})
        self.token_count += estimate_tokens(content)

    def get_context(self) -> list[dict]:
        total = sum(estimate_tokens(m["content"]) for m in self.messages)
        max_ctx = self.config.max_context_tokens
        while total > max_ctx and len(self.messages) > 0:
            removed = self.messages.pop()
            total -= estimate_tokens(removed["content"])
        return list(self.messages)

    def should_reassert(self) -> bool:
        return self.reassertion_count % self.config.reassert_interval == 0

    def get_token_usage(self) -> float:
        return self.token_count / self.config.max_context_tokens
