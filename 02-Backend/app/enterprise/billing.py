"""Billing and invoicing service."""

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class Invoice:
    id: str
    org_id: str
    amount: float
    currency: str
    status: str
    line_items: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BillingManager:
    def __init__(self):
        self._invoices: dict[str, Invoice] = {}

    def create_invoice(self, org_id: str, amount: float, currency: str = "USD", line_items: Optional[list[dict]] = None) -> Invoice:
        invoice_id = str(uuid.uuid4())
        invoice = Invoice(id=invoice_id, org_id=org_id, amount=amount, currency=currency, status="pending", line_items=line_items or [])
        self._invoices[invoice_id] = invoice
        self._persist(invoice)
        return invoice

    def _persist(self, invoice: Invoice):
        with get_db() as conn:
            conn.execute(
                "INSERT INTO invoices (id, org_id, amount, currency, status, line_items, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    invoice.id,
                    invoice.org_id,
                    invoice.amount,
                    invoice.currency,
                    invoice.status,
                    json.dumps(invoice.line_items),
                    invoice.created_at,
                ),
            )
            conn.commit()

    def process_payment(self, invoice_id: str, payment_method: str) -> dict:
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        invoice.status = "paid"
        self._persist(invoice)
        return {"invoice_id": invoice_id, "status": invoice.status, "payment_method": payment_method}

    def get_invoice_history(self, org_id: str) -> list[dict]:
        return [
            {
                "id": inv.id,
                "amount": inv.amount,
                "currency": inv.currency,
                "status": inv.status,
                "created_at": inv.created_at,
            }
            for inv in self._invoices.values()
            if inv.org_id == org_id
        ]


import json

billing_manager = BillingManager()
