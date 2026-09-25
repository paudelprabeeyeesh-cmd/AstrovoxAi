"""Context window manager for token tracking, truncation, and compaction."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TruncationStrategy(str, Enum):
    SLIDING_WINDOW = "sliding_window"
    COMPACT_SUMMARIZE = "compact_summarize"
    PRIORITY_FIRST = "priority_first"
    AGGRESSIVE_COMPACT = "aggressive_compact"


@dataclass
class ContextWindowConfig:
    max_tokens: int = int(os.getenv("CONTEXT_WINDOW_MAX_TOKENS", "128000"))
    reserved_output_tokens: int = int(os.getenv("CONTEXT_WINDOW_RESERVED_OUTPUT", "4096"))
    reserved_system_tokens: int = int(os.getenv("CONTEXT_WINDOW_RESERVED_SYSTEM", "500"))
    max_history_messages: int = int(os.getenv("CONTEXT_WINDOW_MAX_HISTORY", "50"))
    summarization_threshold: float = float(os.getenv("CONTEXT_WINDOW_SUMMARIZE_THRESHOLD", "0.75"))
    strategy: TruncationStrategy = TruncationStrategy.SLIDING_WINDOW


@dataclass
class ContextWindowUsage:
    used_tokens: int = 0
    max_tokens: int = 0
    available_tokens: int = 0
    usage_ratio: float = 0.0
    is_near_limit: bool = False
    is_at_limit: bool = False


class ContextWindowManager:
    def __init__(self, config: Optional[ContextWindowConfig] = None):
        self.config = config or ContextWindowConfig()
        self._usage: dict[str, ContextWindowUsage] = {}

    def measure_message(self, message: dict[str, Any]) -> int:
        content = message.get("content", "") or ""
        if isinstance(content, list):
            return sum(len(str(part)) for part in content) // 4
        return max(1, len(content) // 4)

    def measure_messages(self, messages: list[dict[str, Any]]) -> int:
        return sum(self.measure_message(m) for m in messages)

    def get_usage(self, conversation_id: str) -> ContextWindowUsage:
        return self._usage.get(conversation_id, ContextWindowUsage(
            used_tokens=0,
            max_tokens=self.config.max_tokens,
            available_tokens=self.config.max_tokens,
            usage_ratio=0.0,
            is_near_limit=False,
            is_at_limit=False,
        ))

    def record_usage(self, conversation_id: str, used_tokens: int) -> ContextWindowUsage:
        max_tokens = self.config.max_tokens
        reserved = self.config.reserved_output_tokens + self.config.reserved_system_tokens
        available = max(0, max_tokens - reserved - used_tokens)
        usage_ratio = used_tokens / max_tokens if max_tokens > 0 else 0.0
        usage = ContextWindowUsage(
            used_tokens=used_tokens,
            max_tokens=max_tokens,
            available_tokens=available,
            usage_ratio=round(usage_ratio, 4),
            is_near_limit=usage_ratio >= self.config.summarization_threshold,
            is_at_limit=available <= 0,
        )
        self._usage[conversation_id] = usage
        logger.debug(
            "Context window for %s: %d/%d tokens (%.1f%%), available=%d",
            conversation_id, used_tokens, max_tokens, usage_ratio * 100, available,
        )
        return usage

    def apply_strategy(
        self,
        messages: list[dict[str, Any]],
        conversation_id: str = "default",
        system_prompt: str = "",
    ) -> tuple[list[dict[str, Any]], ContextWindowUsage]:
        system_tokens = max(1, len(system_prompt) // 4) if system_prompt else self.config.reserved_system_tokens
        current_tokens = self.measure_messages(messages) + system_tokens
        usage = self.record_usage(conversation_id, current_tokens)
        if not usage.is_near_limit and not usage.is_at_limit:
            return messages, usage
        logger.info(
            "Applying context strategy '%s' for conversation %s (ratio=%.2f)",
            self.config.strategy.value, conversation_id, usage.usage_ratio,
        )
        if self.config.strategy == TruncationStrategy.SLIDING_WINDOW:
            return self._sliding_window(messages, conversation_id), usage
        if self.config.strategy == TruncationStrategy.COMPACT_SUMMARIZE:
            return self._compact_summarize(messages, conversation_id, system_prompt), usage
        if self.config.strategy == TruncationStrategy.PRIORITY_FIRST:
            return self._priority_first(messages, conversation_id), usage
        if self.config.strategy == TruncationStrategy.AGGRESSIVE_COMPACT:
            return self._aggressive_compact(messages, conversation_id, system_prompt), usage
        return messages, usage

    def _sliding_window(self, messages: list[dict[str, Any]], conversation_id: str) -> list[dict[str, Any]]:
        max_messages = self.config.max_history_messages
        if len(messages) <= max_messages:
            return messages
        return messages[-max_messages:]

    def _compact_summarize(self, messages: list[dict[str, Any]], conversation_id: str, system_prompt: str) -> list[dict[str, Any]]:
        keep = messages[-8:]
        earlier = messages[:-8]
        if not earlier:
            return keep
        summary_input = "\n".join(
            f"{m.get('role', '')}: {(m.get('content', '') or '')[:200]}" for m in earlier
        )
        summary = f"[Summary of earlier conversation: {len(earlier)} messages omitted. Key context compressed.]"
        return [{"role": "system", "content": summary}] + keep

    def _priority_first(self, messages: list[dict[str, Any]], conversation_id: str) -> list[dict[str, Any]]:
        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent_user = [m for m in messages if m.get("role") == "user"]
        recent_assistant = [m for m in messages if m.get("role") == "assistant"]
        max_keep = self.config.max_history_messages
        result = system_msgs
        for msg in recent_user + recent_assistant:
            if len(result) >= max_keep:
                break
            result.append(msg)
        return result

    def _aggressive_compact(self, messages: list[dict[str, Any]], conversation_id: str, system_prompt: str) -> list[dict[str, Any]]:
        keep = messages[-4:]
        earlier = messages[:-4]
        summary_parts = []
        for m in earlier:
            content = (m.get("content", "") or "")[:120]
            summary_parts.append(f"{m.get('role', '')}: {content}")
        summary = "[Compressed history: " + "; ".join(summary_parts[-10:]) + "]"
        return [{"role": "system", "content": summary}] + keep

    def remaining_for_output(self, conversation_id: str) -> int:
        usage = self.get_usage(conversation_id)
        return max(0, usage.available_tokens - self.config.reserved_output_tokens)

    def can_fit(self, conversation_id: str, additional_tokens: int) -> bool:
        return self.remaining_for_output(conversation_id) >= additional_tokens
