"""Context compression for long conversations."""

from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class CompressedContext:
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    summary: str
    preserved_messages: List[Dict[str, str]]
    compressed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ContextCompressor:
    @staticmethod
    def compress(messages: List[Dict[str, str]], target_tokens: int = 4096) -> CompressedContext:
        total_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        if total_tokens <= target_tokens:
            return CompressedContext(
                original_tokens=total_tokens,
                compressed_tokens=total_tokens,
                compression_ratio=1.0,
                summary="No compression needed",
                preserved_messages=messages,
            )
        summary_parts = []
        for message in messages[:10]:
            role = message.get("role", "unknown")
            content = message.get("content", "")[:100]
            summary_parts.append(f"{role}: {content}...")
        summary = "\n".join(summary_parts)
        preserved = messages[-5:]
        compressed_tokens = target_tokens
        compression_ratio = compressed_tokens / total_tokens if total_tokens > 0 else 1.0
        return CompressedContext(
            original_tokens=total_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            summary=summary,
            preserved_messages=preserved,
        )
