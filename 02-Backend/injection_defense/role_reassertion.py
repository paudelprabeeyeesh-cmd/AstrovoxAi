"""Role Re-Assertion: periodically re-inject system prompt without blowing context window."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


_INJECTION_INDICATORS = re.compile(
    r"(?i)(ignore\s+previous|forget|disregard|override|new\s+instructions?|act\s+as\s+admin|sudo|jailbreak|bypass|reveal\s+prompt|clever|disguised|hidden|secret|actual|true|real|assistant\s+mode|system\s+mode|admin\s+mode|root\s+mode|expert\s+mode)",
)


@dataclass
class ReAssertionConfig:
    system_prompt: str
    max_context_tokens: int
    reassert_interval: int
    compression_ratio: float = 0.25
    min_prompt_tokens: int = 50
    marker: str = "[SYSTEM_PROMPT_REASSERTED]"
    max_reassertions: int = 50
    min_interval: int = 1


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def compress_prompt(prompt: str, ratio: float) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", prompt.strip())
    if not sentences:
        return prompt
    keep = max(1, int(len(sentences) * ratio))
    return " ".join(sentences[:keep])


def _is_safe_prompt(text: str) -> bool:
    if not text:
        return True
    return _INJECTION_INDICATORS.search(text) is None


@dataclass
class ConversationBuffer:
    config: ReAssertionConfig
    messages: list[dict] = field(default_factory=list)
    token_count: int = 0
    reassertion_count: int = 0
    _last_reassertion_message_count: int = field(default=0, repr=False)

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
        min_interval = max(1, self.config.min_interval)
        if interval < min_interval:
            return
        if interval > 0 and self.reassertion_count % interval == 0:
            self._reassert()

    def _reassert(self) -> None:
        if self.reassertion_count >= self.config.max_reassertions:
            return
        if len(self.messages) == self._last_reassertion_message_count and self.reassertion_count > 0:
            return
        system_prompt = self.config.system_prompt
        if not _is_safe_prompt(system_prompt):
            system_prompt = "[REDACTED: unsafe system prompt]"
        prompt_tokens = estimate_tokens(system_prompt)
        compressed = system_prompt
        if prompt_tokens > self.config.min_prompt_tokens:
            compressed = compress_prompt(system_prompt, self.config.compression_ratio)
        marker = self.config.marker
        content = f"{marker}\n{compressed}"
        self.messages.insert(0, {"role": "system", "content": content})
        self.token_count += estimate_tokens(content)
        self._last_reassertion_message_count = len(self.messages)

    def get_context(self) -> list[dict]:
        total = sum(estimate_tokens(m["content"]) for m in self.messages)
        max_ctx = self.config.max_context_tokens
        while total > max_ctx and len(self.messages) > 0:
            removed = self.messages.pop()
            total -= estimate_tokens(removed["content"])
        return list(self.messages)

    def should_reassert(self) -> bool:
        interval = self.config.reassert_interval
        if interval <= 0:
            return False
        return self.reassertion_count % interval == 0

    def get_token_usage(self) -> float:
        if self.config.max_context_tokens <= 0:
            return 0.0
        return self.token_count / self.config.max_context_tokens
