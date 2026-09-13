import stripe
import os
from datetime import datetime
from .database import get_db

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

def create_checkout_session(user_id: str, email: str, price_id: str = "price_12345") -> str:
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
