"""Discovery engine for marketplace search and recommendations."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryQuery:
    query: str
    category: Optional[str] = None
    price_range: Optional[tuple[int, int]] = None
    limit: int = 20


class DiscoveryEngine:
    def __init__(self) -> None:
        self._listings: List[Dict[str, Any]] = []

    def index_listing(self, listing: Dict[str, Any]) -> None:
        self._listings.append(listing)

    def search(self, query: DiscoveryQuery) -> List[Dict[str, Any]]:
        results = []
        for listing in self._listings:
            if query.query.lower() in listing.get("name", "").lower():
                if query.category and listing.get("category") != query.category:
                    continue
                results.append(listing)
        return results[: query.limit]


discovery_engine = DiscoveryEngine()
