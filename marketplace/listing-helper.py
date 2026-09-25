import json
import re
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ListingStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


@dataclass
class MarketplaceListing:
    listing_id: str
    name: str
    slug: str
    version: str
    description: str
    author: str
    status: ListingStatus
    tags: List[str] = field(default_factory=list)
    category: str = "utilities"
    homepage_url: str = ""
    repository_url: str = ""
    license: str = "MIT"
    min_platform_version: str = "2.0.0"
    rating: float = 0.0
    download_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class MarketplaceListingHelper:
    def __init__(self, registry_client=None):
        self.registry_client = registry_client
        self._listings: Dict[str, MarketplaceListing] = {}

    def create_listing(self, manifest: Dict[str, Any], author: str) -> MarketplaceListing:
        slug = self._slugify(manifest["name"])
        listing = MarketplaceListing(
            listing_id=manifest.get("listing_id", f"listing-{slug}-{int(datetime.utcnow().timestamp())}"),
            name=manifest["name"],
            slug=slug,
            version=manifest["version"],
            description=manifest.get("description", ""),
            author=author,
            status=ListingStatus.DRAFT,
            tags=manifest.get("tags", []),
            category=manifest.get("category", "utilities"),
            homepage_url=manifest.get("homepage", ""),
            repository_url=manifest.get("repository", ""),
            license=manifest.get("license", "MIT"),
            min_platform_version=manifest.get("min_platform_version", "2.0.0"),
            metadata=manifest.get("metadata", {})
        )
        self._listings[listing.listing_id] = listing
        logger.info(f"Created marketplace listing {listing.listing_id} for {listing.name}")
        return listing

    def validate_listing(self, listing: MarketplaceListing) -> List[str]:
        errors = []
        if not listing.name or len(listing.name) < 3:
            errors.append("Listing name must be at least 3 characters")
        if not listing.description or len(listing.description) < 20:
            errors.append("Listing description must be at least 20 characters")
        if not re.match(r'^[a-z0-9][a-z0-9\-\.]{1,63}$', listing.slug):
            errors.append(f"Invalid slug: {listing.slug}")
        if not listing.author:
            errors.append("Author is required")
        if not re.match(r'^\d+\.\d+\.\d+', listing.version):
            errors.append(f"Version must be semver: {listing.version}")
        if not listing.homepage_url and not listing.repository_url:
            errors.append("At least one of homepage_url or repository_url is required")
        return errors

    def submit_for_review(self, listing_id: str) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        errors = self.validate_listing(listing)
        if errors:
            logger.error(f"Cannot submit listing {listing_id}: {errors}")
            return False
        listing.status = ListingStatus.PENDING_REVIEW
        listing.updated_at = datetime.utcnow().isoformat()
        logger.info(f"Submitted listing {listing_id} for review")
        return True

    def approve_listing(self, listing_id: str) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.status = ListingStatus.APPROVED
        listing.updated_at = datetime.utcnow().isoformat()
        logger.info(f"Approved listing {listing_id}")
        return True

    def reject_listing(self, listing_id: str, reason: str) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.status = ListingStatus.REJECTED
        listing.metadata["rejection_reason"] = reason
        listing.updated_at = datetime.utcnow().isoformat()
        logger.info(f"Rejected listing {listing_id}: {reason}")
        return True

    def deprecate_listing(self, listing_id: str, replacement_slug: Optional[str] = None) -> bool:
        listing = self._listings.get(listing_id)
        if not listing:
            return False
        listing.status = ListingStatus.DEPRECATED
        if replacement_slug:
            listing.metadata["replacement"] = replacement_slug
        listing.updated_at = datetime.utcnow().isoformat()
        logger.info(f"Deprecated listing {listing_id}")
        return True

    def get_listing(self, listing_id: str) -> Optional[MarketplaceListing]:
        return self._listings.get(listing_id)

    def get_by_slug(self, slug: str) -> Optional[MarketplaceListing]:
        for listing in self._listings.values():
            if listing.slug == slug:
                return listing
        return None

    def search(self, query: str = "", category: str = "", tags: Optional[List[str]] = None, status: Optional[List[ListingStatus]] = None) -> List[MarketplaceListing]:
        results = list(self._listings.values())
        if query:
            q = query.lower()
            results = [r for r in results if q in r.name.lower() or q in r.description.lower() or q in r.slug.lower()]
        if category:
            results = [r for r in results if r.category == category]
        if tags:
            results = [r for r in results if any(t in r.tags for t in tags)]
        if status:
            results = [r for r in results if r.status in status]
        return sorted(results, key=lambda r: (-r.rating, -r.download_count))

    def update_stats(self, listing_id: str, downloads: int, rating: float):
        listing = self._listings.get(listing_id)
        if listing:
            listing.download_count = downloads
            listing.rating = rating
            listing.updated_at = datetime.utcnow().isoformat()

    def _slugify(self, name: str) -> str:
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9\-\.]', '-', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        return slug[:64]

    def render_readme(self, listing: MarketplaceListing) -> str:
        readme = f"""# {listing.name}
Version: {listing.version}
Author: {listing.author}
License: {listing.license}

## Description
{listing.description}

## Tags
{', '.join(listing.tags)}

## Links
- Homepage: {listing.homepage_url or 'N/A'}
- Repository: {listing.repository_url or 'N/A'}

## Compatibility
Min platform version: {listing.min_platform_version}
"""
        return readme

    def export_manifest(self, listing: MarketplaceListing) -> Dict[str, Any]:
        return {
            "name": listing.name,
            "slug": listing.slug,
            "version": listing.version,
            "description": listing.description,
            "author": listing.author,
            "license": listing.license,
            "category": listing.category,
            "tags": listing.tags,
            "homepage": listing.homepage_url,
            "repository": listing.repository_url,
            "min_platform_version": listing.min_platform_version,
            "status": listing.status.value,
            "rating": listing.rating,
            "download_count": listing.download_count
        }
