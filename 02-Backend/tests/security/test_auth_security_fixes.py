"""P0 auth security-regression tests (added while fixing the five P0 defects).

Each test that targets a defect is written to FAIL against the pre-fix
code so a regression turns the suite red rather than passing silently:

* P0-1  SHA-256 password hashing is replaced by salted, memory-hard
        ``scrypt``; existing SHA-256 records still verify and are
        transparently rehashed on login; the same password hashes to a
        different value on every call.
* P0-2  Signup must NOT return verification/magic-link tokens.
* P0-3  ``require_verified_email`` must reject unverified users (403).
* P0-4  The signup and password-reset flows must run end to end via
        TestClient with no NameError and correct status codes.
* P0-5  Logout revokes server-side; the previously valid token is then
        rejected.

P0-2 and the signup/reset status-code flow (part of P0-4) are regression
GUARDS: they encode already-correct behaviour and pass before and after
the fix. Every other test is red before the fix and green after.

Notes on strategy:
* ``pytest.ini`` lists ``tests/security`` under ``norecursedirs`` so it is
  excluded from the full product run; passing the file paths explicitly
  on the command line (as the task does) still collects them.
* ``pytest`` is already importable here, so ``app.config``'s production
  guard does not raise and the real modules can be imported.
"""
from __future__ import annotations

import hashlib
import types

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fakes for the endpoint-level tests (P0-2..P0-5).  The live auth router is
# ``app.auth`` (mounted in app/main.py).  We mount only that router in a
# throwaway app and patch the module-level ``supabase`` client so the real
# endpoints run without a live backend.
# ---------------------------------------------------------------------------


class _FakeUser:
    def __init__(self, uid="uid-1", email="user@example.com",
                 email_confirmed_at="2024-01-01T00:00:00Z"):
        self.id = uid
        self.email = email
        self.email_confirmed_at = email_confirmed_at


class _FakeAuth:
    def __init__(self, user: _FakeUser):
        self._user = user

    def sign_up(self, payload):
        return types.SimpleNamespace(user=self._user, session=None)

    def get_user(self, token):
        return types.SimpleNamespace(user=self._user)

    def sign_in_with_password(self, payload):
        return types.SimpleNamespace(
            user=self._user,
            session=types.SimpleNamespace(access_token="acc", refresh_token="ref"),
        )

    def sign_out(self):
        return None

    def reset_password_for_email(self, email, options=None):
        return True


class _FakeSupabase:
    def __init__(self, user: _FakeUser):
        self.auth = _FakeAuth(user)

    def table(self, *a, **k):
        t = types.SimpleNamespace()
        t.select = lambda *a, **k: t
        t.eq = lambda *a, **k: t
        t.execute = lambda: types.SimpleNamespace(data=[])
        return t


def _make_client(monkeypatch, user: _FakeUser) -> TestClient:
    import app.auth as auth

    monkeypatch.setattr(auth, "supabase", _FakeSupabase(user))

    app = FastAPI()
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = auth.limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(auth.router)

    @app.get("/_gated")
    async def _gated(user_id: str = Depends(auth.require_verified_email)):
        return {"user_id": user_id}

    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_slowapi_limiter():
    """Slowapi windows are a process global; clear them so request quotas
    are independent of test execution order (rate limiting is not under test)."""
    import app.auth as auth

    auth.limiter.reset()
    yield
    auth.limiter.reset()


# ===========================================================================
# P0-1  password hashing (service layer) — RED before fix
# ===========================================================================


class _FakeConn:
    def __init__(self, store: dict):
        self._store = store

    def execute(self, clause, params=None):
        self._store["params"] = params
        return types.SimpleNamespace(rowcount=1)

    def commit(self):
        self._store["committed"] = True


class _FakeDB:
    def __init__(self):
        self.store: dict = {}

    def __call__(self, *a, **k):
        return self

    def __enter__(self):
        return _FakeConn(self.store)

    def __exit__(self, *a):
        return False


def test_hash_password_exists_and_is_salted_scrypt():
    import app.services.auth_service as svc

    h1 = svc.hash_password("SamePass!23")
    h2 = svc.hash_password("SamePass!23")
    assert h1.startswith("scrypt$"), f"expected a scrypt marker, got {h1!r}"
    assert h1 != h2, "the same password must hash differently each call (per-hash salt)"


def test_scrypt_record_round_trips_and_rejects_wrong_password():
    import app.services.auth_service as svc

    stored = svc.hash_password("Rightpass!1")
    user = {"id": "x", "password_hash": stored}
    assert svc.verify_password(user, "Rightpass!1") is True
    assert svc.verify_password(user, "wrongpass!1") is False


def test_legacy_sha256_record_verifies_and_is_transparently_rehashed(monkeypatch):
    import app.services.auth_service as svc

    pw = "CorrectHorse!23"
    legacy = hashlib.sha256(pw.encode()).hexdigest()
    user = {"id": "u1", "password_hash": legacy}
    fake = _FakeDB()
    monkeypatch.setattr(svc, "get_db", fake)

    assert svc.verify_password(user, pw) is True
    assert fake.store.get("params") is not None, \
        "a verified legacy SHA-256 record must be transparently rehashed"
    new_hash = fake.store["params"]["h"]
    assert new_hash.startswith("scrypt$")
    assert new_hash != legacy
    assert fake.store.get("committed") is True


def test_legacy_failed_login_is_not_rehashed(monkeypatch):
    import app.services.auth_service as svc

    legacy = hashlib.sha256(b"Rightpass!1").hexdigest()
    user = {"id": "y", "password_hash": legacy}
    fake = _FakeDB()
    monkeypatch.setattr(svc, "get_db", fake)

    assert svc.verify_password(user, "badguess!1") is False
    assert fake.store.get("params") is None, "a failed login must not rewrite the hash"


def test_create_user_stores_scrypt_hash_not_sha256(monkeypatch):
    import app.services.auth_service as svc

    fake = _FakeDB()
    monkeypatch.setattr(svc, "get_db", fake)
    result = svc.create_user("a@b.com", "Str0ng!Pass")
    assert result["email"] == "a@b.com"
    stored = fake.store["params"]["p3"]
    assert stored.startswith("scrypt$"), f"create_user persisted {stored[:8]!r}, not scrypt"


# ===========================================================================
# P0-2  signup must not return tokens (regression guard)
# ===========================================================================


def test_signup_response_has_no_tokens(monkeypatch):
    client = _make_client(monkeypatch, _FakeUser())
    r = client.post("/auth/signup",
                    json={"email": "a@b.com", "password": "Str0ng!Passw0rd", "full_name": "A"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "user" in body
    for banned in ("verification_token", "magic_link_token", "reset_token"):
        assert banned not in body, f"{banned} leaked in signup response"
        assert banned not in repr(body.get("user", {}))


# ===========================================================================
# P0-3  require_verified_email must reject unverified users — RED before fix
# ===========================================================================


def test_require_verified_email_rejects_unverified_user(monkeypatch):
    client = _make_client(monkeypatch, _FakeUser(email_confirmed_at=None))
    r = client.get("/_gated", headers={"Authorization": "Bearer verified-test-token-abcdef0123456789"})
    assert r.status_code == 403, f"unverified user must get 403, got {r.status_code}"


def test_require_verified_email_allows_verified_user(monkeypatch):
    client = _make_client(monkeypatch, _FakeUser(email_confirmed_at="2024-01-01T00:00:00Z"))
    r = client.get("/_gated", headers={"Authorization": "Bearer verified-test-token-abcdef0123456789"})
    assert r.status_code == 200, f"verified user must pass, got {r.status_code}"
    assert r.json()["user_id"] == "uid-1"


def test_require_verified_email_requires_authorization(monkeypatch):
    client = _make_client(monkeypatch, _FakeUser())
    r = client.get("/_gated")
    assert r.status_code == 401


# ===========================================================================
# P0-4  signup + password-reset flows via TestClient, no NameError — GUARD
# ===========================================================================


def test_signup_and_reset_flows_have_correct_status_codes(monkeypatch):
    client = _make_client(monkeypatch, _FakeUser(email="flow@example.com"))

    r = client.post("/auth/signup",
                    json={"email": "flow@example.com", "password": "Str0ng!Passw0rd", "full_name": "F"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "verification_token" not in body and "magic_link_token" not in body

    r2 = client.post("/auth/reset-password", json={"email": "flow@example.com"})
    assert r2.status_code == 200, r2.text
    assert "token" not in r2.json()


# ===========================================================================
# P0-5  logout revokes server-side — RED before fix
# ===========================================================================


def test_logout_revokes_previously_valid_token(monkeypatch):
    client = _make_client(monkeypatch, _FakeUser(email="late@example.com"))
    token = "Bearer late-session-token-abcdefghijklmnopqrstuvwxyz0123456789"

    # The token authenticates the gated dependency before logout ...
    before = client.get("/_gated", headers={"Authorization": token})
    assert before.status_code == 200, f"token should be accepted before logout, got {before.status_code}"

    # ... logout succeeds and reports revocation ...
    out = client.post("/auth/logout", headers={"Authorization": token})
    assert out.status_code == 200, out.text
    assert out.json().get("revoked") is True

    # ... and the SAME token is rejected afterwards.
    after = client.get("/_gated", headers={"Authorization": token})
    assert after.status_code in (401, 403), \
        f"revoked token must be rejected, got {after.status_code}"
