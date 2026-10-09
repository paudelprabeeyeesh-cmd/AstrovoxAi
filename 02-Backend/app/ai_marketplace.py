"""AI Marketplace for prompts, models, and tools."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ListingType(str, Enum):
    PROMPT = "prompt"
    MODEL = "model"
    TOOL = "tool"
    WORKFLOW = "workflow"
    DATASET = "dataset"


class ListingStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class MarketplaceListing:
    listing_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    listing_type: ListingType = ListingType.PROMPT
    title: str = ""
    description: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    price: float = 0.0
    author_id: str = ""
    author_name: str = ""
    status: ListingStatus = ListingStatus.DRAFT
    downloads: int = 0
    rating: float = 0.0
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class AIMarketplace:
    """Marketplace for AI assets."""

    def __init__(self):
        self._listings: Dict[str, MarketplaceListing] = {}

    def publish(self, listing: MarketplaceListing) -> MarketplaceListing:
        listing.status = ListingStatus.PUBLISHED
        listing.updated_at = time.time()
        self._listings[listing.listing_id] = listing
        logger.info("Published marketplace listing: %s", listing.title)
        return listing

    def get_listing(self, listing_id: str) -> Optional[MarketplaceListing]:
        return self._listings.get(listing_id)

    def search(self, query: str, listing_type: Optional[ListingType] = None, limit: int = 20) -> List[MarketplaceListing]:
        results = []
        for listing in self._listings.values():
            if listing.status != ListingStatus.PUBLISHED:
                continue
            if listing_type and listing.listing_type != listing_type:
                continue
            if query.lower() in listing.title.lower() or query.lower() in listing.description.lower():
                results.append(listing)
        results.sort(key=lambda x: x.downloads, reverse=True)
        return results[:limit]

    def increment_downloads(self, listing_id: str) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.downloads += 1
        return True

    def list_by_type(self, listing_type: ListingType) -> List[MarketplaceListing]:
        return [l for l in self._listings.values() if l.listing_type == listing_type and l.status == ListingStatus.PUBLISHED]

    def rate(self, listing_id: str, rating: float) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.rating = (listing.rating + rating) / 2.0
        return True


ai_marketplace = AIMarketplace()
