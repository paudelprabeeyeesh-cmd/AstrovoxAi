"""Shared compression utilities."""

from __future__ import annotations

import re


def compress_text(text: str, max_length: int = 300) -> str:
    """Compress text by removing filler and shortening."""
    filler = re.findall(r"\b(the|a|an|and|or|but|in|on|at|to|for|of|with|by)\b",
                        text.lower())
    words = text.split()
    if len(words) <= max_length:
        return text
    kept = [w for w in words if w.lower() not in filler][:max_length]
    return " ".join(kept) + "..."


def deduplicate_memories(memories: list[dict], threshold: float = 0.85) -> list[dict]:
    """Remove near-duplicate memories."""
    def jaccard(a: str, b: str) -> float:
        sa, sb = set(a.lower().split()), set(b.lower().split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    kept = []
    for m in memories:
        text = m.get("content", m.get("value", "") or "")
        if any(jaccard(text, kept_m.get("content", kept_m.get("value", "")) or "") >= threshold
               for kept_m in kept):
            continue
        kept.append(m)
    return kept


def summarize_memory(memory: dict, length_ratio: float = 0.3) -> dict:
    """Summarize a single memory."""
    text = memory.get("content", memory.get("value", "") or "")
    words = text.split()
    n = max(1, int(len(words) * length_ratio))
    summary = " ".join(words[:n]) + ("..." if len(words) > n else "")
    out = dict(memory)
    out["summary"] = summary
    out["original_length"] = len(words)
    return out
