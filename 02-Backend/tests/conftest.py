import os
import sys
import json
import types
from unittest.mock import patch, MagicMock

# Ensure the backend root is on sys.path so 'app' package can be imported
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

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


def _ensure_module(name):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


def _set_attr_chain(mod_name, attr_name, value):
    mod = sys.modules.get(mod_name)
    if mod is not None:
        setattr(mod, attr_name, value)


# Create top-level aliases for app subpackages that are imported without 'app.' prefix
_alias_map = {
    "utils": "app.utils",
    "utils.auth": "app.utils.auth",
    "utils.auth.auth_utils": "app.utils.auth.auth_utils",
    "repositories": "app.repositories",
    "repositories.database": "app.repositories.database",
    "repositories.database.client": "app.repositories.database.client",
    "repositories.database.supabase_client": "app.repositories.database.supabase_client",
    "middleware": "app.middleware",
    "middleware.security": "app.middleware.security",
    "middleware.security.security_hardening": "app.middleware.security.security_hardening",
    "services": "app.services",
    "services.memory": "app.services.memory",
    "services.memory.memory_manager": "app.services.memory.memory_manager",
    "services.knowledge": "app.services.knowledge",
    "services.knowledge.knowledge_base": "app.services.knowledge.knowledge_base",
    "database": "app.database",
    "api": "app.api",
    "api.routers": "app.api.routers",
    "api.routers.memory": "app.api.routers.memory",
    "api.routers.memory.router": "app.api.routers.memory.router",
    "api.routers.router": "app.api.routers.router",
    "api.routers.workspace_route": "app.api.routers.workspace_route",
    "api.routers.jobs_router": "app.api.routers.jobs_router",
    "api.routers.analytics_route": "app.api.routers.analytics_route",
    "api.routers.knowledge_route": "app.api.routers.knowledge_route",
    "api.routers.agent_route": "app.api.routers.agent_route",
    "api.routers.monitoring_route": "app.api.routers.monitoring_route",
    "api.routers.auth": "app.api.routers.auth",
    "api.routers.auth.security_route": "app.api.routers.auth.security_route",
    "api.routers.admin_route": "app.api.routers.admin_route",
    "api.routers.realtime_route": "app.api.routers.realtime_route",
    "api.routers.dashboard_route": "app.api.routers.dashboard_route",
    "api.v1": "app.api.v1",
    "api.routers.platform_route": "app.api.routers.platform_route",
    "api.routers.knowledge_route_v2": "app.api.routers.knowledge_route_v2",
    "api.routers.neural_router": "app.api.routers.neural_router",
    "api.routers.temporal_route": "app.api.routers.temporal_route",
}

for alias, target in _alias_map.items():
    if alias not in sys.modules:
        try:
            target_mod = __import__(target, fromlist=[""])
            sys.modules[alias] = target_mod
        except ImportError:
            mod = _ensure_module(alias)
            parts = alias.split(".")
            for i in range(len(parts) - 1):
                parent = ".".join(parts[:i + 1])
                child = ".".join(parts[:i + 2])
                if child not in sys.modules:
                    sys.modules[child] = _ensure_module(child)
                if not hasattr(sys.modules[parent], parts[i + 1]):
                    setattr(sys.modules[parent], parts[i + 1], sys.modules[child])

# Ensure app.utils.auth.auth_utils is available
if "app.utils.auth.auth_utils" not in sys.modules:
    try:
        __import__("app.utils.auth.auth_utils", fromlist=[""])
    except ImportError:
        pass

# Create mock for app.metrics
if "app.metrics" not in sys.modules:
    metrics_mod = _ensure_module("app.metrics")
    metrics_mod.track_request = MagicMock()
    metrics_mod.get_metrics = MagicMock(return_value="# HELP\n")
    metrics_mod.CONTENT_TYPE_LATEST = "text/plain"
    metrics_mod.track_ai_request = MagicMock()
    metrics_mod.track_rate_limit = MagicMock()

# Create mock router for missing route modules
from fastapi import APIRouter
_mock_router = APIRouter()

_router_modules = [
    "services.auth.auth",
    "services.vector.embeddings_route",
    "api.routers.memory.router",
    "api.routers.router",
    "api.routers.workspace_route",
    "api.routers.jobs_router",
    "api.routers.analytics_route",
    "api.routers.knowledge_route",
    "api.routers.agent_route",
    "api.routers.monitoring_route",
    "api.routers.auth.security_route",
    "api.routers.admin_route",
    "api.routers.realtime_route",
    "api.routers.dashboard_route",
    "api.v1",
    "api.routers.platform_route",
    "api.routers.knowledge_route_v2",
    "api.routers.neural_router",
    "api.routers.temporal_route",
    "app.kernel.api",
    "app.aios.api",
    "app.api.v1",
]

for mod_name in _router_modules:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = _ensure_module(mod_name)
    sys.modules[mod_name].router = _mock_router
    if mod_name == "api.routers.jobs_router":
        sys.modules[mod_name].events_router = _mock_router

import pytest
from app.database import init_db
try:
    from app.main import app
except Exception:
    from fastapi import FastAPI
    app = FastAPI(title="test")
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
    
    _main_patches = []
    if 'app.main' in sys.modules:
        _main_patches = [
            patch('app.main.llm_client.call_llm', return_value={
                "text": "Mocked answer",
                "provider": "test",
                "model": "test-model",
                "tokens": 10,
                "confidence": 0.9,
            }),
            patch('app.main.llm_client.stream_llm', return_value=iter([
                {"token": "Mocked", "provider": "test", "model": "test-model"},
                {"token": " answer", "provider": "test", "model": "test-model"},
            ])),
        ]

    with patch('app.billing.stripe', mock_stripe), \
         patch.object(billing_module, '_STRIPE_CONFIGURED', True), \
         patch('openai.OpenAI', return_value=mock_openai_client), \
         patch('app.core.moderation.check_moderation', return_value=(False, None)), \
         patch('app.routers.solve.check_moderation', return_value=(False, None)), \
         patch('app.core.providers.get_active_providers', return_value=[]), \
         *_main_patches:
        
        yield {
            'stripe': mock_stripe,
            'openai': mock_openai_client,
        }
    
    if original_stripe is not None:
        billing_module.stripe = original_stripe
    else:
        billing_module.stripe = None
