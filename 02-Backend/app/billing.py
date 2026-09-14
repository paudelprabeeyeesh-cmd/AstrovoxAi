import stripe
import os
from datetime import datetime
from .database import get_db

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "price_pro_123")
STRIPE_TEAM_PRICE_ID = os.getenv("STRIPE_TEAM_PRICE_ID", "price_team_123")
STRIPE_EMBED_PRICE_ID = os.getenv("STRIPE_EMBED_PRICE_ID", "price_embed_123")


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
        conn.execute("UPDATE users SET stripe_customer_id = ? WHERE id = ?", (session.customer, user_id))
        conn.commit()
    return session.url


def cancel_subscription(user_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT stripe_customer_id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not row["stripe_customer_id"]:
            return
        subs = stripe.Subscription.list(customer=row["stripe_customer_id"], status="active")
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
                conn.execute("UPDATE users SET stripe_customer_id = ? WHERE id = ?", (customer_id, user_id))
                conn.execute("UPDATE subscriptions SET plan = 'pro', status = 'active' WHERE user_id = ?", (user_id,))
                conn.commit()
    
    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        with get_db() as conn:
            user = conn.execute("SELECT id FROM users WHERE stripe_customer_id = ?", (customer_id,)).fetchone()
            if user:
                conn.execute("UPDATE subscriptions SET plan = 'free', status = 'canceled' WHERE user_id = ?", (user["id"],))
                conn.commit()
    
    return {"status": "processed", "type": event_type}
