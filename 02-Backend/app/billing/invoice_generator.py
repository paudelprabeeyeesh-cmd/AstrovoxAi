"""Invoice generation."""

from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid


class InvoiceItemType(Enum):
    SUBSCRIPTION = "subscription"
    USAGE = "usage"
    ONE_TIME = "one_time"
    DISCOUNT = "discount"
    TAX = "tax"


@dataclass
class InvoiceItem:
    description: str
    quantity: int
    unit_price: float
    item_type: InvoiceItemType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Invoice:
    invoice_id: str
    user_id: str
    items: List[InvoiceItem]
    subtotal: float
    tax: float
    total: float
    currency: str = "usd"
    status: str = "draft"
    due_date: datetime = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if self.due_date is None:
            self.due_date = datetime.now(timezone.utc) + timedelta(days=30)


class InvoiceGenerator:
    TAX_RATES = {
        "US": 0.0,
        "EU": 0.20,
        "UK": 0.20,
        "CA": 0.05,
        "AU": 0.10,
    }

    @classmethod
    def generate(cls, user_id: str, items: List[InvoiceItem], country: str = "US") -> Invoice:
        invoice_id = f"inv_{uuid.uuid4().hex[:8]}"
        subtotal = sum(item.quantity * item.unit_price for item in items)
        tax_rate = cls.TAX_RATES.get(country.upper(), 0.0)
        tax = subtotal * tax_rate
        total = subtotal + tax
        invoice = Invoice(
            invoice_id=invoice_id,
            user_id=user_id,
            items=items,
            subtotal=subtotal,
            tax=tax,
            total=total,
        )
        return invoice
