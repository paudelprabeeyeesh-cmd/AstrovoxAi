import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

def create_recovery_email(customer_email: str, amount: float, retry_url: str) -> str:
    return f"""
Hi,

Your recent payment of ${amount} failed. Please update your payment method to keep your AstrovoxAI subscription active.

Update payment: {retry_url}

If you have questions, reply to this email.

Thanks,
AstrovoxAI Team
"""
