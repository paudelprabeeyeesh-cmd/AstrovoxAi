"""Stripe webhook handler."""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.webhooks import WebhookEvent, WebhookHandler

logger = logging.getLogger(__name__)


def handle_stripe_event(payload: Dict[str, Any]) -> str:
    event_type = payload.get("type", "unknown")
    logger.info("Stripe event: %s", event_type)
    if event_type == "checkout.session.completed":
        session = payload.get("data", {}).get("object", {})
        customer_id = session.get("customer")
        if customer_id:
            logger.info("Checkout completed for customer %s", customer_id)
    elif event_type == "invoice.payment_failed":
        logger.warning("Payment failed")
    return "ok"


stripe_webhook_handler = WebhookHandler(secret="")
stripe_webhook_handler.register("checkout.session.completed", handle_stripe_event)
stripe_webhook_handler.register("invoice.payment_failed", handle_stripe_event)
