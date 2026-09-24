"""Enhanced plugin marketplace with ratings, versions, and discovery."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginListingStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class PluginListing:
    listing_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plugin_id: str = ""
    name: str = ""
    description: str = ""
    author_id: str = ""
    author_name: str = ""
    version: str = "1.0.0"
    manifest: Dict[str, Any] = field(default_factory=dict)
    status: PluginListingStatus = PluginListingStatus.DRAFT
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class PluginMarketplace:
    def __init__(self):
        self._listings: Dict[str, PluginListing] = {}
        self._ratings: Dict[str, List[float]] = {}

    def publish(self, listing: PluginListing) -> PluginListing:
        listing.status = PluginListingStatus.PUBLISHED
        listing.updated_at = time.time()
        self._listings[listing.listing_id] = listing
        logger.info("Published plugin marketplace listing: %s", listing.name)
        return listing

    def submit(self, listing: PluginListing) -> PluginListing:
        listing.status = PluginListingStatus.DRAFT
        listing.updated_at = time.time()
        self._listings[listing.listing_id] = listing
        logger.info("Submitted plugin listing: %s", listing.name)
        return listing

    def approve(self, listing_id: str) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.status = PluginListingStatus.PUBLISHED
        listing.updated_at = time.time()
        logger.info("Approved plugin listing: %s", listing.name)
        return True

    def reject(self, listing_id: str) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.status = PluginListingStatus.REJECTED
        listing.updated_at = time.time()
        return True

    def get_listing(self, listing_id: str) -> Optional[PluginListing]:
        return self._listings.get(listing_id)

    def search(
        self,
        query: str = "",
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[PluginListing]:
        results = []
        for listing in self._listings.values():
            if listing.status != PluginListingStatus.PUBLISHED:
                continue
            if category and listing.category != category:
                continue
            if tags and not any(tag in listing.tags for tag in tags):
                continue
            if query:
                q = query.lower()
                if q not in listing.name.lower() and q not in listing.description.lower():
                    continue
            results.append(listing)
        results.sort(key=lambda x: (x.rating * 0.5 + x.downloads * 0.5), reverse=True)
        return results[:limit]

    def increment_downloads(self, listing_id: str) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.downloads += 1
        return True

    def rate(self, listing_id: str, rating: float) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        if listing_id not in self._ratings:
            self._ratings[listing_id] = []
        self._ratings[listing_id].append(max(0.0, min(5.0, rating)))
        ratings = self._ratings[listing_id]
        listing.rating = round(sum(ratings) / len(ratings), 2)
        listing.rating_count = len(ratings)
        listing.updated_at = time.time()
        return True

    def list_by_category(self, category: str) -> List[PluginListing]:
        return [
            l for l in self._listings.values()
            if l.category == category and l.status == PluginListingStatus.PUBLISHED
        ]

    def list_by_tag(self, tag: str) -> List[PluginListing]:
        return [
            l for l in self._listings.values()
            if tag in l.tags and l.status == PluginListingStatus.PUBLISHED
        ]

    def archive(self, listing_id: str) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.status = PluginListingStatus.ARCHIVED
        listing.updated_at = time.time()
        return True

    def get_stats(self) -> Dict[str, Any]:
        published = [l for l in self._listings.values() if l.status == PluginListingStatus.PUBLISHED]
        return {
            "total_listings": len(self._listings),
            "published": len(published),
            "total_downloads": sum(l.downloads for l in published),
            "avg_rating": round(sum(l.rating for l in published) / len(published), 2) if published else 0.0,
            "categories": list({l.category for l in published}),
        }


plugin_marketplace = PluginMarketplace()
