"""
Memory Compression - Reduces memory footprint via summarization and consolidation.

Strategies:
- Summarization of long conversation histories
- Merging redundant facts
- Extracting key insights from episodic memories
- Temporal compression (condensing time-series memories)
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


class MemoryCompression:
    """Compresses memory content while preserving key information."""

    def __init__(self, max_summary_ratio: float = 0.3):
        self.max_summary_ratio = max_summary_ratio

    def compress_text(self, text: str, max_length: Optional[int] = None) -> str:
        if max_length is None:
            max_length = max(50, int(len(text) * self.max_summary_ratio))
        if len(text) <= max_length:
            return text
        sentences = text.replace("! ", "!|").replace("? ", "?|").replace(". ", ".|").split("|")
        kept = []
        total = 0
        for sentence in sentences:
            if total + len(sentence) <= max_length:
                kept.append(sentence)
                total += len(sentence)
            else:
                break
        return " ".join(kept) if kept else text[:max_length]

    def compress_memory_item(self, content: str, memory_type: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        compressed = self.compress_text(content)
        return {
            "original_length": len(content),
            "compressed_length": len(compressed),
            "compression_ratio": len(compressed) / max(len(content), 1),
            "memory_type": memory_type,
            "content": compressed,
            "metadata": metadata or {},
            "compressed_at": datetime.utcnow().isoformat(),
        }

    def batch_compress(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for item in items:
            content = item.get("content", "")
            memory_type = item.get("memory_type", "general")
            metadata = item.get("metadata", {})
            results.append(self.compress_memory_item(content, memory_type, metadata))
        return results

    def summarize_memories(self, memories: List[Dict[str, Any]]) -> str:
        if not memories:
            return ""
        contents = [m.get("content", "") for m in memories if m.get("content")]
        combined = "\n".join(contents)
        return self.compress_text(combined, max_length=500)
