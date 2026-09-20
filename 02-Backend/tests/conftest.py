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


@pytest.fixture(scope="session", autouse=True)
def mock_external_services():
    """Mock external services that require API keys."""
    
    import app.billing as billing_module
    original_stripe = getattr(billing_module, 'stripe', None)
    mock_stripe = MagicMock()
    billing_module.stripe = mock_stripe
    billing_module._STRIPE_CONFIGURED = True
    
    # Create a mock OpenAI client that returns proper responses
    mock_openai_client = MagicMock()
    
    # Mock embeddings response
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [MagicMock()]
    mock_embedding_response.data[0].embedding = [0.1] * 1536
    mock_openai_client.embeddings.create.return_value = mock_embedding_response
    
    # Mock moderation response - safe content
    mock_moderation_response = MagicMock()
    mock_moderation_result = MagicMock()
    mock_moderation_result.categories = MagicMock()
    # Make all category checks return False
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
         patch('app.core.router.call_llm', return_value={
             "text": "Mocked answer",
             "provider": "test",
             "model": "test-model",
             "tokens": 10,
             "confidence": 0.9,
         }), \
         patch('app.core.router.call_llm_stream', return_value=iter([
             {"token": "Mocked", "provider": "test", "model": "test-model"},
             {"token": " answer", "provider": "test", "model": "test-model"},
         ])), \
         patch('app.core.moderation.check_moderation', return_value=(False, None)), \
         patch('app.core.providers.get_active_providers', return_value=[]):
        
        yield {
            'stripe': mock_stripe,
            'openai': mock_openai_client,
        }
    
    if original_stripe is not None:
        billing_module.stripe = original_stripe
    else:
        billing_module.stripe = None
