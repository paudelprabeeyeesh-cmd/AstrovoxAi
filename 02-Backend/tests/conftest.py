<<<<<<< HEAD
"""Pytest configuration for the canonical FastAPI backend.

Sets dummy Supabase credentials before the app is imported so the shared
client can be constructed without real secrets, and exposes the backend
package on sys.path.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Backend root (02-Backend) so `import app.main` resolves.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Dummy creds: the health/readiness/root routes never call Supabase, but the
# shared client is created at import time and requires these to be set.
os.environ.setdefault("VITE_SUPABASE_URL", "https://dummy.supabase.co")
os.environ.setdefault("VITE_SUPABASE_ANON_KEY", "dummy-anon-key")


@pytest.fixture(autouse=True)
def mock_supabase_auth():
    """Mock Supabase auth for all tests."""
    mock_user = MagicMock()
    mock_user.id = "test-user-id"
    mock_user.email = "test@example.com"
=======
import os
import sys
import json
from unittest.mock import patch, MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("ASTROVOX_DB", "test.db")
os.environ.setdefault("ASTROVOX_TEST_MODE", "1")
if not os.getenv("ASTROVOX_ENCRYPTION_KEY"):
    os.environ["ASTROVOX_ENCRYPTION_KEY"] = "HSMTYGgSppCPt3g3VAorkpAX4GR0W8T3ILpsKLfblns="

os.environ.setdefault("GROQ_API_KEY", "gsk_dummy")
os.environ.setdefault("GEMINI_API_KEY", "AIzaSyDummy")
os.environ.setdefault("MISTRAL_API_KEY", "MISTRAL_DUMMY")
os.environ.setdefault("OPENROUTER_API_KEY", "sk-or-dummy")
os.environ.setdefault("HF_API_KEY", "hf_dummy")
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
os.environ.setdefault("STRIPE_PRO_PRICE_ID", "price_dummy")
os.environ.setdefault("STRIPE_TEAM_PRICE_ID", "price_dummy")
os.environ.setdefault("STRIPE_EMBED_PRICE_ID", "price_dummy")
os.environ.setdefault("STRIPE_PREMIUM_ACTION_PRICE_ID", "price_dummy")

import pytest
from app.database import init_db
from app.main import app
from fastapi.testclient import TestClient

DB_PATH = os.environ.get("ASTROVOX_DB", "test.db")

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()
    yield
    for ext in ["", "-shm", "-wal"]:
        p = DB_PATH + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except PermissionError:
                pass
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838

    mock_response = MagicMock()
    mock_response.user = mock_user

<<<<<<< HEAD
    mock_auth = MagicMock()
    mock_auth.get_user.return_value = mock_response

    mock_client = MagicMock()
    mock_client.auth = mock_auth

    with patch("app.auth_utils.get_supabase", return_value=mock_client):
        with patch("app.supabase_client.get_supabase", return_value=mock_client):
            yield
=======
@pytest.fixture(scope="session", autouse=True)
def mock_external_services():
    """Mock external services that require API keys."""
    
    import app.billing as billing_module
    original_stripe = getattr(billing_module, 'stripe', None)
    mock_stripe = MagicMock()
    billing_module.stripe = mock_stripe
    billing_module._STRIPE_CONFIGURED = True
    
    mock_openai_client = MagicMock()
    
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [MagicMock()]
    mock_embedding_response.data[0].embedding = [0.1] * 1536
    mock_openai_client.embeddings.create.return_value = mock_embedding_response
    
    mock_moderation_response = MagicMock()
    mock_moderation_result = MagicMock()
    mock_moderation_result.categories = MagicMock()
    mock_moderation_result.categories.hate = False
    mock_moderation_result.categories.hate_threatening = False
    mock_moderation_result.categories.self_harm = False
    mock_moderation_result.categories.sexual = False
    mock_moderation_result.categories.sexual_minors = False
    mock_moderation_result.categories.violence = False
    mock_moderation_result.categories.violence_graphic = False
    mock_moderation_response.results = [mock_moderation_result]
    mock_openai_client.moderations.create.return_value = mock_moderation_response
    
    with patch('app.billing.stripe', mock_stripe), \
         patch.object(billing_module, '_STRIPE_CONFIGURED', True), \
         patch('openai.OpenAI', return_value=mock_openai_client), \
         patch('app.main.llm_client.call_llm', return_value={
             "text": "Mocked answer",
             "provider": "test",
             "model": "test-model",
             "tokens": 10,
             "confidence": 0.9,
         }), \
         patch('app.main.llm_client.stream_llm', return_value=iter([
             {"token": "Mocked", "provider": "test", "model": "test-model"},
             {"token": " answer", "provider": "test", "model": "test-model"},
         ])), \
         patch('app.core.moderation.check_moderation', return_value=(False, None)), \
         patch('app.routers.solve.check_moderation', return_value=(False, None)), \
         patch('app.core.providers.get_active_providers', return_value=[]):
        
        yield {
            'stripe': mock_stripe,
            'openai': mock_openai_client,
        }
    
    if original_stripe is not None:
        billing_module.stripe = original_stripe
    else:
        billing_module.stripe = None
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838
