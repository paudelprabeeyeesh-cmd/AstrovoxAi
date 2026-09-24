from typing import List, Dict


class ContextCompressor:
    def __init__(self, max_compression_ratio: float = 0.5):
        if max_compression_ratio <= 0 or max_compression_ratio > 1:
            raise ValueError("max_compression_ratio must be between 0 and 1")
        self.max_compression_ratio = max_compression_ratio

    def compress(self, text: str) -> str:
        words = text.split()
        if not words:
            return text
        keep = max(1, int(len(words) * self.max_compression_ratio))
        return " ".join(words[:keep])

    def compress_turns(self, turns: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not turns:
            return []
        compressed: List[Dict[str, str]] = []
        for turn in turns:
            content = turn.get("content", "")
            compressed.append({
                "role": turn.get("role", "user"),
                "content": self.compress(content),
            })
        return compressed

    def compression_ratio(self, original: str, compressed: str) -> float:
        original_len = len(original.split())
        compressed_len = len(compressed.split())
        if original_len == 0:
            return 1.0
        return compressed_len / original_len
