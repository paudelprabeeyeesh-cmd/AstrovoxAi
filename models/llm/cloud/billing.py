import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PricingTier:
    tier_id: str
    name: str
    monthly_price: float
    included_tokens: int
    overage_rate_per_token: float


@dataclass
class InvoiceLineItem:
    description: str
    quantity: float
    unit_price: float
    amount: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Invoice:
    invoice_id: str
    developer_id: str
    period_start: datetime
    period_end: datetime
    line_items: List[InvoiceLineItem] = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "usd"
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.utcnow)


class BillingSystem:
    def __init__(self) -> None:
        self._invoices: Dict[str, Invoice] = {}
        self._usage: Dict[str, List[Dict[str, Any]]] = {}
        self._tiers: Dict[str, PricingTier] = {}

    def register_tier(self, tier: PricingTier) -> None:
        self._tiers[tier.tier_id] = tier

    def record_usage(
        self,
        developer_id: str,
        tokens_in: int,
        tokens_out: int,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        entry = {
            "event_id": str(uuid.uuid4()),
            "developer_id": developer_id,
            "model_id": model_id,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": tokens_in + tokens_out,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._usage.setdefault(developer_id, []).append(entry)
        return entry

    def get_usage_summary(
        self,
        developer_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        start = start or datetime.utcnow() - timedelta(days=30)
        end = end or datetime.utcnow()
        events = [
            e for e in self._usage.get(developer_id, [])
            if start <= datetime.fromisoformat(e["timestamp"]) <= end
        ]
        total_tokens = sum(e["total_tokens"] for e in events)
        return {
            "developer_id": developer_id,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "total_events": len(events),
            "total_tokens": total_tokens,
        }

    def generate_invoice(
        self,
        developer_id: str,
        tier_id: str,
        period_start: datetime,
        period_end: datetime,
        tax_rate: float = 0.0,
    ) -> Invoice:
        if tier_id not in self._tiers:
            raise KeyError(f"Pricing tier not found: {tier_id}")
        tier = self._tiers[tier_id]
        usage = self.get_usage_summary(developer_id, period_start, period_end)
        total_tokens = usage["total_tokens"]
        overage = max(0, total_tokens - tier.included_tokens)
        overage_cost = overage * tier.overage_rate_per_token
        monthly_cost = tier.monthly_price
        subtotal = monthly_cost + overage_cost

        line_items = [
            InvoiceLineItem(
                description=f"{tier.name} Plan",
                quantity=1.0,
                unit_price=monthly_cost,
                amount=monthly_cost,
            ),
        ]
        if overage_cost > 0:
            line_items.append(InvoiceLineItem(
                description="Overage charges",
                quantity=overage,
                unit_price=tier.overage_rate_per_token,
                amount=overage_cost,
                metadata={"included_tokens": tier.included_tokens, "total_tokens": total_tokens},
            ))

        invoice = Invoice(
            invoice_id=str(uuid.uuid4()),
            developer_id=developer_id,
            period_start=period_start,
            period_end=period_end,
            line_items=line_items,
            subtotal=round(subtotal, 4),
            tax=round(subtotal * tax_rate, 4),
            total=round(subtotal * (1 + tax_rate), 4),
        )
        self._invoices[invoice.invoice_id] = invoice
        logger.info("Generated invoice %s for developer %s", invoice.invoice_id, developer_id)
        return invoice

    def get_invoice(self, invoice_id: str) -> Invoice:
        if invoice_id not in self._invoices:
            raise KeyError(f"Invoice not found: {invoice_id}")
        return self._invoices[invoice_id]

    def list_invoices(self, developer_id: str) -> List[Invoice]:
        return [inv for inv in self._invoices.values() if inv.developer_id == developer_id]
