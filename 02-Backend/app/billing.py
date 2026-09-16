import os
import logging

import stripe

from .database import get_db

logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID")
STRIPE_TEAM_PRICE_ID = os.getenv("STRIPE_TEAM_PRICE_ID")
STRIPE_EMBED_PRICE_ID = os.getenv("STRIPE_EMBED_PRICE_ID")
STRIPE_PREMIUM_ACTION_PRICE_ID = os.getenv("STRIPE_PREMIUM_ACTION_PRICE_ID")

if not all([STRIPE_PRO_PRICE_ID, STRIPE_TEAM_PRICE_ID, STRIPE_EMBED_PRICE_ID, STRIPE_PREMIUM_ACTION_PRICE_ID]):
    raise RuntimeError("STRIPE_PRO_PRICE_ID, STRIPE_TEAM_PRICE_ID, STRIPE_EMBED_PRICE_ID, and STRIPE_PREMIUM_ACTION_PRICE_ID must be set")

MAX_CONSECUTIVE_FAILURES = 3


def _get_user_by_customer_id(customer_id: str):
    with get_db() as conn:
        return conn.execute(
            "SELECT id, email, plan FROM users WHERE stripe_customer_id = ?",
            (customer_id,),
        ).fetchone()


def _increment_failed_payment_count(user_id: str) -> int:
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET failed_payment_count = COALESCE(failed_payment_count, 0) + 1 WHERE id = ?",
            (user_id,),
        )
        row = conn.execute(
            "SELECT failed_payment_count FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        conn.commit()
        return row["failed_payment_count"] if row else 0


def _reset_failed_payment_count(user_id: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET failed_payment_count = 0 WHERE id = ?",
            (user_id,),
        )
        conn.commit()


def _downgrade_to_free(user_id: str, customer_id: str):
    with get_db() as conn:
        conn.execute("UPDATE users SET plan = 'free' WHERE id = ?", (user_id,))
        subs = stripe.Subscription.list(
            customer=customer_id, status="active"
        )
        for sub in subs:
            stripe.Subscription.modify(sub.id, cancel_at_period_end=True)
        conn.execute(
            "UPDATE subscriptions SET plan = 'free', status = 'canceled' WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()


def _log_notification(user_id: str, message: str):
    logger.info(f"[NOTIFICATION] user={user_id} {message}")


def create_checkout_session(user_id: str, email: str, price_id: str = None) -> str:
    price_id = price_id or STRIPE_PRO_PRICE_ID
    session = stripe.checkout.Session.create(
        customer_email=email,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url="https://astrovox.ai/success",
        cancel_url="https://astrovox.ai/cancel",
        metadata={"user_id": user_id},
    )
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
            (session.customer, user_id),
        )
        conn.commit()
    return session.url


def create_premium_checkout_session(user_id: str, email: str) -> str:
    """Create checkout for one-time premium action ($29)."""
    session = stripe.checkout.Session.create(
        customer_email=email,
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PREMIUM_ACTION_PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url="https://astrovox.ai/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://astrovox.ai/cancel",
        metadata={"user_id": user_id, "type": "premium_action"},
    )
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
            (session.customer, user_id),
        )
        conn.commit()
    return session.url


def cancel_subscription(user_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT stripe_customer_id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row or not row["stripe_customer_id"]:
            return
        subs = stripe.Subscription.list(
            customer=row["stripe_customer_id"], status="active"
        )
        for sub in subs:
            stripe.Subscription.modify(sub.id, cancel_at_period_end=True)
        conn.execute("UPDATE users SET plan = 'free' WHERE id = ?", (user_id,))
        conn.commit()


def handle_stripe_webhook(payload: bytes, sig_header: str) -> dict:
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        raise ValueError(f"Invalid webhook signature: {e}")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        user_id = data.get("metadata", {}).get("user_id")
        if user_id:
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
                    (customer_id, user_id),
                )
                conn.execute(
                    "UPDATE subscriptions SET plan = 'pro', status = 'active' WHERE user_id = ?",
                    (user_id,),
                )
                conn.execute(
                    "UPDATE users SET plan = 'pro' WHERE id = ?",
                    (user_id,),
                )
                conn.commit()

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        with get_db() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE stripe_customer_id = ?", (customer_id,)
            ).fetchone()
            if user:
                conn.execute(
                    "UPDATE subscriptions SET plan = 'free', status = 'canceled' WHERE user_id = ?",
                    (user["id"],),
                )
                conn.execute(
                    "UPDATE users SET plan = 'free' WHERE id = ?",
                    (user["id"],),
                )
                conn.commit()

    elif event_type == "invoice.payment_succeeded":
        customer_id = data.get("customer")
        with get_db() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE stripe_customer_id = ?", (customer_id,)
            ).fetchone()
            if user:
                _reset_failed_payment_count(user["id"])
                amount = data.get("amount_paid", 0) / 100
                conn.execute(
                    "INSERT INTO usage (id, user_id, tokens, cost, model, cached, error, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(__import__('uuid').uuid4()),
                        user["id"],
                        0,
                        amount,
                        "stripe_subscription",
                        0,
                        None,
                        __import__('datetime').datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        user = _get_user_by_customer_id(customer_id)
        if user:
            failed_count = _increment_failed_payment_count(user["id"])
            _log_notification(
                user["id"],
                f"Payment failed ({failed_count}/{MAX_CONSECUTIVE_FAILURES}).",
            )
            if failed_count >= MAX_CONSECUTIVE_FAILURES:
                _downgrade_to_free(user["id"], customer_id)
                _log_notification(
                    user["id"],
                    "Downgraded to free plan after repeated payment failures.",
                )

    elif event_type == "invoice.payment_requires_action":
        customer_id = data.get("customer")
        user = _get_user_by_customer_id(customer_id)
        if user:
            _log_notification(
                user["id"],
                "Payment requires authentication (3D Secure).",
            )

    return {"status": "processed", "type": event_type}
