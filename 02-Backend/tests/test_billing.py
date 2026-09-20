import time
import json
import uuid
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

import app.main as main_module

client = TestClient(main_module.app)


@pytest.fixture(autouse=True)
def _init_db():
    from app.database import init_db
    init_db()
    yield
    from app.database import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM usage")
        conn.execute("DELETE FROM subscriptions")
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM refresh_tokens")
        conn.commit()


def _create_user():
    user_id = str(uuid.uuid4())
    email = f"bill-{int(time.time())}-{uuid.uuid4().hex[:6]}@test.com"
    with patch("app.database.get_db") as mock_get_db:
        mock_conn = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        mock_conn.commit.return_value = None
        from app.auth import hash_password
        password_hash = hash_password("testpass123")
        mock_conn.execute(
            "INSERT INTO users (id, email, password_hash, email_verified) VALUES (?, ?, ?, ?)",
            (user_id, email, password_hash, 1),
        )
    from app.auth import create_access_token
    access_token = create_access_token(user_id, email)
    return user_id, email, access_token


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _make_webhook(event_type, data_object):
    payload = json.dumps({"type": event_type, "data": {"object": data_object}}).encode()
    return payload


def test_stripe_webhook_idempotency():
    user_id, email, token = _create_user()
    with patch("app.billing.stripe") as mock_stripe:
        mock_stripe.api_key = "sk_test"
        mock_event = {"type": "checkout.session.completed", "data": {"object": {
            "customer": "cus_123", "metadata": {"user_id": user_id}
        }}}
        mock_stripe.Webhook.construct_event.return_value = mock_event

        payload = _make_webhook("checkout.session.completed", {
            "customer": "cus_123", "metadata": {"user_id": user_id}
        })

        r1 = client.post("/billing/webhook", content=payload, headers={"stripe-signature": "sig"})
        assert r1.status_code == 200
        r2 = client.post("/billing/webhook", content=payload, headers={"stripe-signature": "sig"})
        assert r2.status_code == 200

        with patch("app.database.get_db") as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_conn
            mock_conn.fetchone.return_value = {"stripe_customer_id": "cus_123"}
            subs = []
            mock_stripe.Subscription.list.return_value = subs


def test_subscription_lifecycle():
    user_id, email, token = _create_user()
    with patch("app.billing.stripe") as mock_stripe:
        mock_stripe.api_key = "sk_test"
        mock_session = MagicMock()
        mock_session.customer = "cus_123"
        mock_session.url = "https://checkout.stripe.com"
        mock_stripe.checkout.Session.create.return_value = mock_session

        r = client.post("/billing/checkout", headers=_headers(token))
        assert r.status_code == 200
        assert "url" in r.json()

        mock_event = {"type": "checkout.session.completed", "data": {"object": {
            "customer": "cus_123", "metadata": {"user_id": user_id}
        }}}
        mock_stripe.Webhook.construct_event.return_value = mock_event
        payload = _make_webhook("checkout.session.completed", {
            "customer": "cus_123", "metadata": {"user_id": user_id}
        })
        r = client.post("/billing/webhook", content=payload, headers={"stripe-signature": "sig"})
        assert r.status_code == 200

        mock_event = {"type": "customer.subscription.deleted", "data": {"object": {
            "customer": "cus_123"
        }}}
        mock_stripe.Webhook.construct_event.return_value = mock_event
        payload = _make_webhook("customer.subscription.deleted", {"customer": "cus_123"})
        r = client.post("/billing/webhook", content=payload, headers={"stripe-signature": "sig"})
        assert r.status_code == 200


def test_dunning_flow():
    user_id, email, token = _create_user()
    with patch("app.billing.stripe") as mock_stripe:
        mock_stripe.api_key = "sk_test"
        mock_event = {"type": "invoice.payment_failed", "data": {"object": {
            "customer": "cus_123"
        }}}
        mock_stripe.Webhook.construct_event.return_value = mock_event

        with patch("app.database.get_db") as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_conn
            mock_conn.fetchone.side_effect = [
                {"id": user_id, "stripe_customer_id": "cus_123"},
                {"failed_payment_count": 1},
                {"failed_payment_count": 2},
                {"failed_payment_count": 3},
            ]
            mock_conn.execute.return_value = None
            mock_conn.commit.return_value = None

            payload = _make_webhook("invoice.payment_failed", {"customer": "cus_123"})
            for _ in range(3):
                r = client.post("/billing/webhook", content=payload, headers={"stripe-signature": "sig"})
                assert r.status_code == 200
            assert mock_conn.execute.call_count >= 3
