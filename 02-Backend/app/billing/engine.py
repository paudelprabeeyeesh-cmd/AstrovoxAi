"""Billing engine."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum


class BillingStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class InvoiceStatus(Enum):
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    PAID = "paid"
    OVERDUE = "overdue"
    VOID = "void"


@dataclass
class Invoice:
    invoice_id: str
    user_id: str
    amount: float
    currency: str = "usd"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    due_date: datetime = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    paid_at: Optional[datetime] = None

    def __post_init__(self):
        if self.due_date is None:
            self.due_date = datetime.now(timezone.utc) + timedelta(days=30)


class BillingEngine:
    _invoices: Dict[str, Invoice] = {}

    @classmethod
    def create_invoice(cls, user_id: str, amount: float, line_items: List[Dict[str, Any]]) -> Invoice:
        invoice_id = f"inv_{user_id}_{len(cls._invoices)}"
        invoice = Invoice(
            invoice_id=invoice_id,
            user_id=user_id,
            amount=amount,
            line_items=line_items,
        )
        cls._invoices[invoice_id] = invoice
        return invoice

    @classmethod
    def mark_paid(cls, invoice_id: str) -> Optional[Invoice]:
        invoice = cls._invoices.get(invoice_id)
        if invoice:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.now(timezone.utc)
        return invoice
