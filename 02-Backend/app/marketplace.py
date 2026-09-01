"""AI Marketplace — plugins, prompts, agents, workflows."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MarketplaceItem:
    """An item in the marketplace."""
    id: str
    name: str
    description: str
    item_type: str
    author: str
    version: str
    downloads: int = 0
    rating: float = 0.0
    ratings_count: int = 0
    created_at: float = 0.0
    tags: list = field(default_factory=list)

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class Marketplace:
    """AI Marketplace."""

    def __init__(self):
        self._items: dict[str, MarketplaceItem] = {}

    def publish(self, name: str, description: str, item_type: str, author: str, version: str = "1.0.0", tags: list = None) -> MarketplaceItem:
        """Publish an item."""
        import secrets
        item = MarketplaceItem(
            id=secrets.token_hex(8),
            name=name,
            description=description,
            item_type=item_type,
            author=author,
            version=version,
            tags=tags or [],
        )
        self._items[item.id] = item
        return item

    def search(self, query: str, item_type: str = None) -> list:
        query_lower = query.lower()
        results = [
            i for i in self._items.values()
            if query_lower in i.name.lower() or query_lower in i.description.lower()
        ]
        if item_type:
            results = [i for i in results if i.item_type == item_type]
        return results

    def rate(self, item_id: str, rating: float):
        item = self._items.get(item_id)
        if item:
            total = item.rating * item.ratings_count + rating
            item.ratings_count += 1
            item.rating = total / item.ratings_count

    def download(self, item_id: str):
        item = self._items.get(item_id)
        if item:
            item.downloads += 1


marketplace = Marketplace()
