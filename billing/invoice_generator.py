"""
Invoice generation for AstrovoxAI.
Generates invoices based on usage and subscriptions.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class InvoiceItem:
    description: str
    quantity: float
    unit_price: float
    amount: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "amount": self.amount,
            "metadata": self.metadata,
        }


@dataclass
class Invoice:
    invoice_id: str
    developer_id: str
    subscription_id: Optional[str]
    period_start: datetime
    period_end: datetime
    items: List[InvoiceItem] = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "usd"
    status: str = "draft"
    due_date: Optional[datetime] = None
    pdf_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "developer_id": self.developer_id,
            "subscription_id": self.subscription_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "items": [item.to_dict() for item in self.items],
            "subtotal": self.subtotal,
            "tax": self.tax,
            "total": self.total,
            "currency": self.currency,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "pdf_url": self.pdf_url,
            "created_at": self.created_at.isoformat(),
        }


class InvoiceGenerator:
    """Generates invoices from usage data and subscriptions."""

    def __init__(self, billing_address_provider: Optional[Any] = None):
        self._billing_address_provider = billing_address_provider

    def generate_invoice(
        self,
        developer_id: str,
        subscription_id: Optional[str],
        usage_summary: Any,
        plan: Any,
        period_start: datetime,
        period_end: datetime,
        tax_rate: float = 0.0,
    ) -> Invoice:
        items: List[InvoiceItem] = []
        if plan and plan.price_monthly > 0:
            items.append(InvoiceItem(
                description=f"{plan.name} Plan",
                quantity=1.0,
                unit_price=plan.price_monthly,
                amount=plan.price_monthly,
            ))
        if usage_summary and usage_summary.estimated_cost > 0:
            items.append(InvoiceItem(
                description="Usage-based charges",
                quantity=1.0,
                unit_price=usage_summary.estimated_cost,
                amount=usage_summary.estimated_cost,
                metadata={"breakdown": usage_summary.breakdown},
            ))
        subtotal = sum(item.amount for item in items)
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        invoice = Invoice(
            invoice_id=str(uuid.uuid4()),
            developer_id=developer_id,
            subscription_id=subscription_id,
            period_start=period_start,
            period_end=period_end,
            items=items,
            subtotal=round(subtotal, 4),
            tax=round(tax_amount, 4),
            total=round(total, 4),
            due_date=period_end + timedelta(days=30),
        )
        logger.info("Generated invoice %s for developer %s", invoice.invoice_id, developer_id)
        return invoice

    def finalize_invoice(self, invoice: Invoice) -> Invoice:
        invoice.status = "finalized"
        logger.info("Finalized invoice %s", invoice.invoice_id)
        return invoice

    def mark_invoice_paid(self, invoice: Invoice, payment_id: str) -> Invoice:
        invoice.status = "paid"
        logger.info("Marked invoice %s as paid with payment %s", invoice.invoice_id, payment_id)
        return invoice
