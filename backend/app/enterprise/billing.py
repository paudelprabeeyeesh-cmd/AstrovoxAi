"""Billing and invoicing service."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Invoice:
    id: str
    org_id: str
    amount: float
    currency: str
    status: str
    line_items: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    paid_at: Optional[str] = None


class BillingManager:
    def __init__(self):
        self._invoices: Dict[str, Invoice] = {}

    def create_invoice(self, org_id: str, amount: float, currency: str = "USD", line_items: Optional[List[dict]] = None) -> Invoice:
        invoice_id = str(uuid.uuid4())
        invoice = Invoice(
            id=invoice_id,
            org_id=org_id,
            amount=amount,
            currency=currency,
            status="pending",
            line_items=line_items or [],
        )
        self._invoices[invoice_id] = invoice
        logger.info("Created invoice %s for org %s amount %s %s", invoice_id, org_id, amount, currency)
        return invoice

    def process_payment(self, invoice_id: str, payment_method: str) -> dict:
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc).isoformat()
        logger.info("Processed payment for invoice %s via %s", invoice_id, payment_method)
        return {"invoice_id": invoice_id, "status": invoice.status, "payment_method": payment_method}

    def get_invoice_history(self, org_id: str) -> List[dict]:
        return [
            {
                "id": inv.id,
                "amount": inv.amount,
                "currency": inv.currency,
                "status": inv.status,
                "created_at": inv.created_at,
                "paid_at": inv.paid_at,
            }
            for inv in self._invoices.values()
            if inv.org_id == org_id
        ]


billing_manager = BillingManager()
