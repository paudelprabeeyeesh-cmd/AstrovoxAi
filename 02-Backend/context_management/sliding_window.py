from typing import List, Dict, Optional


class SlidingWindow:
    def __init__(self, max_tokens: int = 1000):
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        self.max_tokens = max_tokens
        self.window: List[Dict[str, int]] = []
        self.evicted_count = 0

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def add(self, content: str, metadata: Optional[Dict] = None) -> Dict:
        tokens = self._estimate_tokens(content)
        entry = {"content": content, "tokens": tokens}
        if metadata:
            entry.update(metadata)
        self.window.append(entry)
        self._enforce_boundary()
        return entry

    def _enforce_boundary(self) -> None:
        while self.total_tokens() > self.max_tokens and len(self.window) > 0:
            self.window.pop(0)
            self.evicted_count += 1

    def total_tokens(self) -> int:
        return sum(e["tokens"] for e in self.window)

    def get_window(self) -> List[Dict]:
        return list(self.window)

    def clear(self) -> None:
        self.window.clear()
        self.evicted_count = 0
