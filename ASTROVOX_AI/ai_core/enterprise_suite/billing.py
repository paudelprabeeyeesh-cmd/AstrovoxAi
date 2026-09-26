"""AI billing."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIInvoice:
    invoice_id: str
    tenant_id: str
    amount_cents: int
    currency: str
    status: str = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AIBilling:
    def __init__(self) -> None:
        self._invoices: Dict[str, AIInvoice] = {}

    def create_invoice(self, tenant_id: str, amount_cents: int, currency: str = "USD") -> AIInvoice:
        invoice_id = uuid.uuid4().hex
        invoice = AIInvoice(invoice_id=invoice_id, tenant_id=tenant_id, amount_cents=amount_cents, currency=currency)
        self._invoices[invoice_id] = invoice
        return invoice

    def get_invoice(self, invoice_id: str) -> Optional[AIInvoice]:
        return self._invoices.get(invoice_id)


ai_billing = AIBilling()
