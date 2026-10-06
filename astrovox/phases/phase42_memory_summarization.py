"""Automated memory summarization."""

from __future__ import annotations

from astrovox.phases._shared.compression import summarize_memory


def summarize_conversation(messages: list[dict]) -> str:
    """Generate a summary of a conversation."""
    if not messages:
        return ""
    texts = [m.get("content", m.get("value", "") or "") for m in messages]
    combined = " ".join(texts)
    words = combined.split()
    n = min(len(words), 60)
    return " ".join(words[:n]) + ("..." if len(words) > n else "")


def summarize_memory_batch(memories: list[dict]) -> list[dict]:
    """Summarize multiple memories."""
    return [summarize_memory(m) for m in memories]
