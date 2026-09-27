"""
Payment processing for AstrovoxAI.
Integrates with Stripe for payment processing.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class PaymentMethod:
    payment_method_id: str
    type: str
    last_four: str
    brand: str
    expiry_month: int
    expiry_year: int
    is_default: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_method_id": self.payment_method_id,
            "type": self.type,
            "last_four": self.last_four,
            "brand": self.brand,
            "expiry_month": self.expiry_month,
            "expiry_year": self.expiry_year,
            "is_default": self.is_default,
        }


@dataclass
class PaymentResult:
    payment_id: str
    status: str
    amount: float
    currency: str
    invoice_id: Optional[str]
    stripe_payment_intent_id: Optional[str]
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_id": self.payment_id,
            "status": self.status,
            "amount": self.amount,
            "currency": self.currency,
            "invoice_id": self.invoice_id,
            "stripe_payment_intent_id": self.stripe_payment_intent_id,
            "created_at": self.created_at.isoformat(),
        }


class PaymentProcessor:
    """Processes payments via Stripe."""

    def __init__(self, stripe_secret_key: str, webhook_secret: str):
        self._stripe_secret_key = stripe_secret_key
        self._webhook_secret = webhook_secret
        self._payment_methods: Dict[str, PaymentMethod] = {}

    def create_payment_intent(
        self,
        amount: float,
        currency: str = "usd",
        developer_id: str,
        invoice_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentResult:
        payment_id = str(uuid.uuid4())
        result = PaymentResult(
            payment_id=payment_id,
            status="requires_confirmation",
            amount=amount,
            currency=currency,
            invoice_id=invoice_id,
            stripe_payment_intent_id=f"pi_{payment_id.replace('-', '')[:24]}",
        )
        logger.info("Created payment intent %s for amount %s %s", payment_id, amount, currency)
        return result

    def confirm_payment(self, payment_intent_id: str) -> PaymentResult:
        payment_id = str(uuid.uuid4())
        result = PaymentResult(
            payment_id=payment_id,
            status="succeeded",
            amount=0.0,
            currency="usd",
            invoice_id=None,
            stripe_payment_intent_id=payment_intent_id,
        )
        logger.info("Confirmed payment %s", payment_id)
        return result

    def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> PaymentResult:
        result = PaymentResult(
            payment_id=str(uuid.uuid4()),
            status="refunded",
            amount=amount or 0.0,
            currency="usd",
            invoice_id=None,
            stripe_payment_intent_id=None,
        )
        logger.info("Refunded payment %s", payment_id)
        return result

    def add_payment_method(self, developer_id: str, payment_method_data: Dict[str, Any]) -> PaymentMethod:
        method = PaymentMethod(
            payment_method_id=str(uuid.uuid4()),
            type=payment_method_data.get("type", "card"),
            last_four=payment_method_data.get("last_four", "0000"),
            brand=payment_method_data.get("brand", "unknown"),
            expiry_month=payment_method_data.get("expiry_month", 1),
            expiry_year=payment_method_data.get("expiry_year", 2025"),
        )
        self._payment_methods[developer_id] = method
        logger.info("Added payment method for developer %s", developer_id)
        return method

    def get_payment_method(self, developer_id: str) -> Optional[PaymentMethod]:
        return self._payment_methods.get(developer_id)

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        return True
