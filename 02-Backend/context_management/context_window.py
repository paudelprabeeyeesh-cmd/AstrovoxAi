from typing import List, Dict, Optional


class ContextWindow:
    def __init__(self, max_tokens: int = 1000):
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        self.max_tokens = max_tokens
        self.entries: List[Dict[str, object]] = []
        self.overflow_count = 0

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def add(self, text: str, metadata: Optional[Dict] = None) -> Dict:
        tokens = self._estimate_tokens(text)
        entry: Dict[str, object] = {"text": text, "tokens": tokens}
        if metadata:
            entry.update(metadata)
        self.entries.append(entry)
        self._enforce_limit()
        return entry

    def _enforce_limit(self) -> None:
        while self.total_tokens() > self.max_tokens and len(self.entries) > 0:
            self.entries.pop(0)
            self.overflow_count += 1

    def total_tokens(self) -> int:
        return sum(int(e["tokens"]) for e in self.entries)

    def get_window(self) -> List[Dict[str, object]]:
        return list(self.entries)

    def clear(self) -> None:
        self.entries.clear()
        self.overflow_count = 0
