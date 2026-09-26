"""Billing and invoicing for enterprise customers."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    record_id: str
    org_id: str
    service: str
    quantity: float
    unit: str
    unit_price: float
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Invoice:
    invoice_id: str
    org_id: str
    amount_cents: int
    currency: str
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BillingManager:
    def __init__(self) -> None:
        self._usage: List[UsageRecord] = []
        self._invoices: Dict[str, Invoice] = {}

    def record_usage(self, org_id: str, service: str, quantity: float, unit: str, unit_price: float) -> UsageRecord:
        record = UsageRecord(
            record_id=uuid.uuid4().hex,
            org_id=org_id,
            service=service,
            quantity=quantity,
            unit=unit,
            unit_price=unit_price,
        )
        self._usage.append(record)
        return record

    def create_invoice(self, org_id: str, amount_cents: int, currency: str = "USD") -> Invoice:
        invoice_id = uuid.uuid4().hex
        invoice = Invoice(invoice_id=invoice_id, org_id=org_id, amount_cents=amount_cents, currency=currency)
        self._invoices[invoice_id] = invoice
        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        return self._invoices.get(invoice_id)


billing_manager = BillingManager()
