import os
import sys
import slowapi
from unittest.mock import patch, MagicMock

_backend = os.path.join(os.path.dirname(os.path.dirname(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

os.environ.setdefault("VITE_SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("VITE_SUPABASE_ANON_KEY", "dummy-anon-key")
os.environ.setdefault("ASTROVOX_DB", "test.db")
os.environ.setdefault("ASTROVOX_TEST_MODE", "1")
os.environ.setdefault("GROQ_API_KEY", "gsk_dummy")
os.environ.setdefault("GEMINI_API_KEY", "AIzaSyDummy")
os.environ.setdefault("MISTRAL_API_KEY", "MISTRAL_DUMMY")
os.environ.setdefault("OPENROUTER_API_KEY", "sk-or-dummy")
os.environ.setdefault("HF_API_KEY", "hf_dummy")
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
os.environ.setdefault("STRIPE_PRICE_ID", "price_dummy")
os.environ.setdefault("STRIPE_TEAM_PRICE_ID", "price_dummy")
os.environ.setdefault("STRIPE_EMBED_PRICE_ID", "price_dummy")
os.environ.setdefault("STRIPE_PREMIUM_ACTION_PRICE_ID", "price_dummy")

_original_limit = slowapi.Limiter.limit

def _noop_limit(self, *args, **kwargs):
    def decorator(func):
        return func
    return decorator

slowapi.Limiter.limit = _noop_limit

_fake_supabase = MagicMock()
_fake_supabase.auth.sign_up.return_value = MagicMock(
    user=MagicMock(id="user-1", email="test@test.com"),
    session=MagicMock(access_token="access-1", refresh_token="refresh-1"),
)
_fake_supabase.auth.sign_in_with_password.return_value = _fake_supabase.auth.sign_up.return_value
_fake_supabase.auth.get_user.return_value = MagicMock(
    user=MagicMock(id="user-1", email="test@test.com", app_metadata={"roles": ["user"]})
)
_fake_supabase.auth.refresh_session.return_value = MagicMock(
    session=MagicMock(access_token="new-access-1", refresh_token="new-refresh-1")
)
_fake_supabase.auth.reset_password_for_email.return_value = MagicMock()
_fake_supabase.auth.sign_in_with_otp.return_value = MagicMock()

def _fake_table(name):
    table = MagicMock()
    table.insert.return_value = table
    table.select.return_value = table
    table.eq.return_value = table
    table.update.return_value = table
    table.delete.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.range.return_value = table
    table.execute.return_value = MagicMock(data=[])
    _fake_supabase.table.return_value = table
    return table

_fake_supabase.table.side_effect = _fake_table

supabase_patcher = patch("app.supabase_client.get_supabase", return_value=_fake_supabase)
supabase_patcher.start()

_fake_health = MagicMock()
_fake_health.get_overall_health.return_value = {
    "status": "healthy",
    "components": {
        "database": {"status": "healthy", "message": "ok", "latency_ms": 0.0},
        "redis": {"status": "degraded", "message": "not configured", "latency_ms": 0.0},
        "memory": {"status": "degraded", "message": "skipped", "latency_ms": 0.0},
        "disk": {"status": "degraded", "message": "skipped", "latency_ms": 0.0},
        "llm_providers": {
            "openai": {"status": "degraded", "message": "not configured", "latency_ms": 0.0},
            "anthropic": {"status": "degraded", "message": "not configured", "latency_ms": 0.0},
            "gemini": {"status": "degraded", "message": "not configured", "latency_ms": 0.0},
            "groq": {"status": "degraded", "message": "not configured", "latency_ms": 0.0},
        },
    },
    "timestamp": "2026-01-01T00:00:00Z",
}
_fake_health.is_healthy.return_value = True
_fake_health.history.return_value = []

try:
    import app.health as _health_mod
    _health_mod.health_service = _fake_health
except Exception as _e:  # noqa: BLE001
    pass
