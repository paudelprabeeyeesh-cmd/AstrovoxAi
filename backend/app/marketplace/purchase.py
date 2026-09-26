"""Purchase management for marketplace transactions."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Purchase:
    purchase_id: str
    listing_id: str
    buyer_id: str
    amount_cents: int
    status: str = "pending"
    purchased_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PurchaseManager:
    def __init__(self) -> None:
        self._purchases: Dict[str, Purchase] = {}

    def create_purchase(self, listing_id: str, buyer_id: str, amount_cents: int) -> Purchase:
        purchase_id = uuid.uuid4().hex
        purchase = Purchase(purchase_id=purchase_id, listing_id=listing_id, buyer_id=buyer_id, amount_cents=amount_cents)
        self._purchases[purchase_id] = purchase
        return purchase

    def complete_purchase(self, purchase_id: str) -> Optional[Purchase]:
        purchase = self._purchases.get(purchase_id)
        if purchase:
            purchase.status = "completed"
        return purchase


purchase_manager = PurchaseManager()
