"""Memory compression: summarization and deduplication of memories."""

from __future__ import annotations

import re


def compress_text(text: str, max_length: int = 300) -> str:
    """Compress text by removing filler and shortening."""
    filler = re.findall(r"(the|a|an|and|or|but|in|on|at|to|for|of|with|by)",
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


class MemoryCompressor:
    """Compresses and deduplicates memory collections."""

    def __init__(self, max_length: int = 300, dedup_threshold: float = 0.85):
        self.max_length = max_length
        self.dedup_threshold = dedup_threshold

    def compress(self, memory: dict) -> dict:
        content = memory.get("content", memory.get("value", "") or "")
        out = dict(memory)
        out["content"] = compress_text(content, self.max_length)
        return out

    def compress_batch(self, memories: list[dict]) -> list[dict]:
        compressed = [self.compress(m) for m in memories]
        return deduplicate_memories(compressed, self.dedup_threshold)

    def stats(self, original: list[str], compressed: list[str]) -> dict:
        orig_total = sum(len(t.split()) for t in original)
        comp_total = sum(len(t.split()) for t in compressed)
        return {"original_tokens": orig_total, "compressed_tokens": comp_total,
                "reduction_pct": (1 - comp_total / max(orig_total, 1)) * 100}
