import os

import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

PRICES = {
    "free": {"requests": 10, "amount": 0},
    "pro": {"requests": 1000, "amount": 9},
    "team": {"requests": 10000, "amount": 25},
}


def get_plan_limits(plan: str) -> dict:
    return PRICES.get(plan, PRICES["free"])


def create_team_checkout(user_id: str, email: str, seat_count: int = 1) -> str:
    price_id = os.getenv("STRIPE_TEAM_PRICE_ID", "price_team_123")
    session = stripe.checkout.Session.create(
        customer_email=email,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": seat_count}],
        mode="subscription",
        success_url="https://astrovox.ai/success",
        cancel_url="https://astrovox.ai/cancel",
        metadata={"user_id": user_id},
    )
    return session.url


def create_embed_subscription(user_id: str, email: str) -> str:
    price_id = os.getenv("STRIPE_EMBED_PRICE_ID", "price_embed_123")
    session = stripe.checkout.Session.create(
        customer_email=email,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url="https://astrovox.ai/success",
        cancel_url="https://astrovox.ai/cancel",
        metadata={"user_id": user_id},
    )
    return session.url
