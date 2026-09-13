"""Integration marketplace: catalog, search, ratings, install/uninstall, notifications."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .plugins import (
    PluginLifecycleError,
    PluginManifest,
    PluginState,
)
from .manager import get_plugin_manager


class ListingCategory(str, Enum):
    DEVELOPER = "developer"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    STORAGE = "storage"
    ANALYTICS = "analytics"
    SECURITY = "security"
    GENERAL = "general"


@dataclass
class ListingRating:
    user_id: str
    stars: int
    review: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Listing:
    id: str
    name: str
    version: str
    description: str
    category: str
    tags: List[str]
    author: str
    icon: str = ""
    homepage: str = ""
    permissions: List[str] = field(default_factory=list)
    downloads: int = 0
    rating_avg: float = 0.0
    rating_count: int = 0
    installed: bool = False
    enabled: bool = False
    featured: bool = False
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version_history: List[Dict[str, Any]] = field(default_factory=list)
    permissions_overview: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketplaceCatalog:
    """Browseable catalog of plugins and integrations."""

    PERMISSION_DESCRIPTIONS: Dict[str, str] = {
        "memory:read": "Read long-term memory for the authenticated user.",
        "memory:write": "Create or modify memory entries for the user.",
        "files:read": "Read files stored in AstrovoxAI storage.",
        "files:write": "Write or delete files in AstrovoxAI storage.",
        "network:outgoing": "Make outbound HTTPS calls to external services.",
        "network:incoming": "Receive inbound webhooks or HTTP calls.",
        "code:execute": "Execute arbitrary code in a sandboxed runtime.",
        "users:read": "Read profile information about other users.",
        "billing:read": "Read billing and subscription data.",
        "agent:run": "Trigger agent runs on behalf of the user.",
        "webhook:publish": "Publish webhook events to subscribed endpoints.",
        "storage:read": "Read objects from managed storage.",
        "storage:write": "Write objects to managed storage.",
    }

    def __init__(self) -> None:
        self.listings: Dict[str, Listing] = {}
        self._ratings: Dict[str, List[ListingRating]] = defaultdict(list)

    # ---- catalog management -----------------------------------------

    def register(self, listing: Listing) -> Listing:
        if not listing.permissions_overview:
            listing.permissions_overview = {
                p: self.PERMISSION_DESCRIPTIONS.get(p, "Custom permission")
                for p in listing.permissions
            }
        self.listings[listing.id] = listing
        return listing

    def register_from_manifest(self, manifest: PluginManifest) -> Listing:
        listing_id = manifest.id
        listing = self.listings.get(listing_id) or Listing(
            id=listing_id,
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            category=manifest.category,
            tags=manifest.tags,
            author=manifest.author,
            icon=manifest.icon,
            homepage=manifest.homepage,
            permissions=manifest.permissions,
        )
        listing.version = manifest.version
        listing.permissions = manifest.permissions
        listing.description = manifest.description or listing.description
        listing.tags = manifest.tags or listing.tags
        listing.author = manifest.author or listing.author
        listing.homepage = manifest.homepage or listing.homepage
        listing.icon = manifest.icon or listing.icon
        listing.version_history.append(
            {
                "version": manifest.version,
                "released_at": datetime.now(timezone.utc).isoformat(),
                "checksum": manifest.checksum,
                "size_bytes": manifest.size_bytes,
            }
        )
        return self.register(listing)

    def remove(self, listing_id: str) -> Optional[Listing]:
        return self.listings.pop(listing_id, None)

    # ---- search -----------------------------------------------------

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        sort: str = "popular",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        results: List[Listing] = []
        for listing in self.listings.values():
            if category and listing.category != category:
                continue
            if tag and tag not in listing.tags:
                continue
            if query:
                haystack = " ".join(
                    [listing.name, listing.description, " ".join(listing.tags)]
                ).lower()
                if query.lower() not in haystack:
                    continue
            results.append(listing)
        if sort == "recent":
            results.sort(key=lambda l: l.updated_at, reverse=True)
        elif sort == "rating":
            results.sort(key=lambda l: (l.rating_avg, l.rating_count), reverse=True)
        else:
            results.sort(key=lambda l: l.downloads, reverse=True)
        return [r.to_dict() for r in results[:limit]]

    def categories(self) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = defaultdict(int)
        for listing in self.listings.values():
            counts[listing.category] += 1
        return [
            {"category": cat, "count": cnt}
            for cat, cnt in sorted(counts.items(), key=lambda kv: -kv[1])
        ]

    # ---- ratings ----------------------------------------------------

    def add_rating(self, listing_id: str, rating: ListingRating) -> Optional[Listing]:
        if listing_id not in self.listings:
            return None
        if rating.stars < 1 or rating.stars > 5:
            raise ValueError("Stars must be between 1 and 5")
        self._ratings[listing_id].append(rating)
        listing = self.listings[listing_id]
        listing.rating_count = len(self._ratings[listing_id])
        listing.rating_avg = sum(r.stars for r in self._ratings[listing_id]) / listing.rating_count
        return listing

    def ratings_for(self, listing_id: str) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._ratings.get(listing_id, [])]

    # ---- install / uninstall ---------------------------------------

    def install(
        self,
        listing_id: str,
        permissions: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        manager = get_plugin_manager()
        listing = self.listings.get(listing_id)
        if listing is None:
            raise PluginLifecycleError(f"Listing '{listing_id}' not found")
        manifest = PluginManifest(
            id=listing.id,
            name=listing.name,
            version=listing.version,
            author=listing.author,
            description=listing.description,
            category=listing.category,
            tags=listing.tags,
            permissions=listing.permissions,
            entry_point=f"{listing.id}_plugin:Plugin",
        )
        try:
            record = manager.install(manifest, permissions=permissions, config=config)
        except PluginLifecycleError:
            raise
        listing.downloads += 1
        listing.installed = True
        listing.enabled = record.state == PluginState.ENABLED
        listing.version = record.manifest.version
        return {
            "listing": listing.to_dict(),
            "record": record.to_dict(),
        }

    def uninstall(self, listing_id: str) -> Dict[str, Any]:
        manager = get_plugin_manager()
        try:
            record = manager.uninstall(listing_id)
        except PluginLifecycleError as exc:
            raise
        listing = self.listings.get(listing_id)
        if listing is not None:
            listing.installed = False
            listing.enabled = False
        return {
            "listing": listing.to_dict() if listing else None,
            "record": record.to_dict() if record else None,
        }

    def toggle(self, listing_id: str, enabled: bool) -> Dict[str, Any]:
        manager = get_plugin_manager()
        try:
            record = manager.enable(listing_id) if enabled else manager.disable(listing_id)
        except PluginLifecycleError as exc:
            raise
        listing = self.listings.get(listing_id)
        if listing is not None:
            listing.enabled = enabled
        return {
            "listing": listing.to_dict() if listing else None,
            "record": record.to_dict(),
        }

    def sync_installed(self) -> None:
        manager = get_plugin_manager()
        for record in manager.registry.all():
            listing = self.listings.get(record.manifest.id)
            if listing is None:
                listing = self.register_from_manifest(record.manifest)
            listing.installed = True
            listing.enabled = record.state == PluginState.ENABLED
            listing.version = record.manifest.version

    def notifications(self) -> List[Dict[str, Any]]:
        manager = get_plugin_manager()
        notifs: List[Dict[str, Any]] = []
        for record in manager.registry.all():
            listing = self.listings.get(record.manifest.id)
            if listing is None:
                continue
            if listing.version != record.manifest.version:
                notifs.append(
                    {
                        "listing_id": listing.id,
                        "installed_version": record.manifest.version,
                        "available_version": listing.version,
                        "name": listing.name,
                        "type": "update_available",
                    }
                )
        return notifs


_GLOBAL_CATALOG: Optional[MarketplaceCatalog] = None


def get_marketplace_catalog() -> MarketplaceCatalog:
    global _GLOBAL_CATALOG
    if _GLOBAL_CATALOG is None:
        _GLOBAL_CATALOG = MarketplaceCatalog()
    return _GLOBAL_CATALOG


def seed_default_catalog() -> None:
    """Populate the catalog with bundled plugins so the marketplace isn't empty."""

    catalog = get_marketplace_catalog()
    manager = get_plugin_manager()
    if catalog.listings:
        return
    bundled_ids = [
        "github",
        "slack",
        "discord",
        "notion",
        "jira",
        "gdrive",
    ]
    for plugin_id in bundled_ids:
        try:
            record = manager.install(plugin_id)
            catalog.register_from_manifest(record.manifest)
        except Exception:
            continue
    for listing_id, listing in catalog.listings.items():
        listing.featured = listing_id in {"github", "slack", "notion", "gdrive"}
        listing.downloads = 1024 + hash(listing_id) % 4096
        listing.rating_count = 32 + hash(listing_id) % 80
        listing.rating_avg = round(4.0 + (hash(listing_id) % 10) / 10.0, 1)