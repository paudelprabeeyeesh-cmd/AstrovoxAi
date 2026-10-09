from typing import List, Dict


class ContextRetriever:
    def __init__(self, max_items: int = 10):
        if max_items < 1:
            raise ValueError("max_items must be at least 1")
        self.max_items = max_items
        self.store: List[Dict] = []

    def add(self, item: Dict) -> None:
        if "text" not in item:
            raise ValueError("item must contain 'text'")
        self.store.append(dict(item))

    def retrieve(self, query: str) -> List[Dict]:
        if not query:
            return []
        scored = []
        query_terms = set(query.lower().split())
        for item in self.store:
            text_terms = set(item.get("text", "").lower().split())
            overlap = len(query_terms & text_terms)
            scored.append((overlap, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[: self.max_items]]

    def clear(self) -> None:
        self.store.clear()
