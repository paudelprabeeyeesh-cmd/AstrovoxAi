"""Marketplace listing management."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MarketplaceListing:
    listing_id: str
    name: str
    category: str
    price_cents: int
    seller_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ListingManager:
    def __init__(self) -> None:
        self._listings: Dict[str, MarketplaceListing] = {}

    def create_listing(self, listing: MarketplaceListing) -> MarketplaceListing:
        listing.listing_id = listing.listing_id or uuid.uuid4().hex
        self._listings[listing.listing_id] = listing
        return listing

    def get_listing(self, listing_id: str) -> Optional[MarketplaceListing]:
        return self._listings.get(listing_id)

    def search(self, category: Optional[str] = None) -> List[MarketplaceListing]:
        listings = list(self._listings.values())
        if category:
            listings = [l for l in listings if l.category == category]
        return listings


listing_manager = ListingManager()
