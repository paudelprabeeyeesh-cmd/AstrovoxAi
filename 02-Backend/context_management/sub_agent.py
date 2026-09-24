from typing import List, Dict


class SubAgentDelegator:
    def __init__(self, context_limit: int = 2000, compression_ratio: float = 0.5):
        if context_limit < 1:
            raise ValueError("context_limit must be at least 1")
        if not (0.0 < compression_ratio <= 1.0):
            raise ValueError("compression_ratio must be in (0, 1]")
        self.context_limit = context_limit
        self.compression_ratio = compression_ratio
        self.delegations: List[Dict] = []

    def _compress(self, text: str, max_tokens: int) -> str:
        words = text.split()
        keep = max(1, int(len(words) * self.compression_ratio))
        return " ".join(words[:keep]) + "..."

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def delegate(self, subtask: str, context: str) -> Dict:
        original_tokens = self._estimate_tokens(context)
        max_tokens = int(self.context_limit * self.compression_ratio)
        compressed = self._compress(context, max_tokens)
        compressed_tokens = self._estimate_tokens(compressed)
        delegation = {
            "subtask": subtask,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "context": compressed,
            "within_limit": compressed_tokens <= self.context_limit,
        }
        self.delegations.append(delegation)
        return delegation

    def get_delegation_count(self) -> int:
        return len(self.delegations)

    def get_compression_stats(self) -> Dict[str, float]:
        if not self.delegations:
            return {"count": 0, "avg_ratio": 0.0, "avg_original": 0.0, "avg_compressed": 0.0}
        total_original = sum(d["original_tokens"] for d in self.delegations)
        total_compressed = sum(d["compressed_tokens"] for d in self.delegations)
        count = len(self.delegations)
        return {
            "count": count,
            "avg_ratio": total_compressed / total_original if total_original > 0 else 0.0,
            "avg_original": total_original / count,
            "avg_compressed": total_compressed / count,
        }
