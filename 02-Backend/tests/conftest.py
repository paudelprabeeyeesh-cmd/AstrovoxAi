import os
import sys
import json
import types
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

# Create mock modules for missing imports before importing app.main
_missing_modules = [
    "services",
    "services.auth",
    "services.auth.auth",
    "services.vector",
    "services.vector.embeddings_route",
    "api",
    "api.routers",
    "api.routers.memory",
    "api.routers.memory.router",
    "api.routers.router",
    "api.routers.workspace_route",
    "api.routers.jobs_router",
    "api.routers.analytics_route",
    "api.routers.knowledge_route",
    "api.routers.agent_route",
    "api.routers.monitoring_route",
    "api.routers.auth",
    "api.routers.auth.security_route",
    "api.routers.admin_route",
    "api.routers.realtime_route",
    "api.routers.dashboard_route",
    "api.v1",
    "api.routers.platform_route",
    "api.routers.knowledge_route_v2",
    "api.routers.neural_router",
    "api.routers.temporal_route",
]

for mod_name in _missing_modules:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

# Ensure nested modules have parent attributes
for mod_name in _missing_modules:
    mod = sys.modules[mod_name]
    parts = mod_name.split(".")
    for i in range(len(parts) - 1):
        parent_name = ".".join(parts[:i + 1])
        child_name = ".".join(parts[:i + 2])
        if child_name in sys.modules and not hasattr(sys.modules[parent_name], parts[i + 1]):
            setattr(sys.modules[parent_name], parts[i + 1], sys.modules[child_name])

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
