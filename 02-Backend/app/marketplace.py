<<<<<<< HEAD
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
=======
import uuid

from .database import get_db


def create_prompt(user_id: str, title: str, prompt: str, price: float = 0) -> str:
    prompt_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO marketplace_prompts (id, user_id, title, prompt, price) VALUES (?, ?, ?, ?, ?)",
            (prompt_id, user_id, title, prompt, price),
        )
        conn.commit()
    return prompt_id


def list_prompts() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, prompt, price, downloads, created_at FROM marketplace_prompts ORDER BY downloads DESC"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "prompt": r["prompt"],
                "price": r["price"],
                "downloads": r["downloads"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]


def get_prompt(prompt_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, prompt, price, downloads, created_at FROM marketplace_prompts WHERE id = ?",
            (prompt_id,),
        ).fetchone()
        if not row:
            raise ValueError("Prompt not found")
        return {
            "id": row["id"],
            "title": row["title"],
            "prompt": row["prompt"],
            "price": row["price"],
            "downloads": row["downloads"],
            "created_at": row["created_at"],
        }


def increment_downloads(prompt_id: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE marketplace_prompts SET downloads = downloads + 1 WHERE id = ?",
            (prompt_id,),
        )
        conn.commit()
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838
