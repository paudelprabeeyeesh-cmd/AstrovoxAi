import importlib
import os
import sys
import types
import asyncio
from contextlib import ExitStack
from unittest.mock import patch, MagicMock

import pytest

# slowapi's `@limiter.limit` decorators are disabled BEFORE `app.main` is
# imported further down. Doing it here rather than in the integration conftest
# is what makes it effective: `app.main` registers its limits at import time,
# and that import already happened by the time the integration conftest loads,
# so the decorators there were neutering nothing. Left enabled, SlowAPIMiddleware
# enforces its own 30/minute window and every chat request returns 429.

try:
    import slowapi

    def _noop_limit(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    slowapi.Limiter.limit = _noop_limit
except Exception:  # noqa: BLE001 - slowapi is optional
    pass

def _run(func, *args, **kwargs):
    result = func(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return asyncio.run(result)
    return result

pytest.run = _run

# Ensure the backend root is on sys.path so 'app' package can be imported.
# The backend root MUST take precedence over both the project root and the
# current working directory: the project root also contains an `app` package
# (a different one), and Python resolves `import app` to whichever comes
# first on sys.path.
_backend_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_project_root = os.path.dirname(_backend_root)

# Remove any earlier project-root / CWD entries, and any entry that would let
# `app` resolve to the wrong package.
_preferred = [_backend_root]
for _entry in list(sys.path):
    _abs = os.path.abspath(_entry)
    if _abs == _backend_root:
        continue
    if _abs in (_project_root, os.getcwd()) or _abs.startswith(_project_root + os.sep + "app"):
        continue
    _preferred.append(_entry)
sys.path[:] = _preferred

# Drop `app` (and submodules) already imported from the wrong location so the
# next import re-resolves against the backend root.
_app = sys.modules.get("app")
_app_path = list(getattr(_app, "__path__", []) or [])
if _app_path and not any(
    os.path.abspath(os.path.dirname(p)) == _backend_root for p in _app_path
):
    for _name in [n for n in list(sys.modules) if n == "app" or n.startswith("app.")]:
        del sys.modules[_name]

os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("ASTROVOX_DB", "test.db")
os.environ.setdefault("ASTROVOX_TEST_MODE", "1")
# HTTPS enforcement is a deployment concern: the test transport speaks plain
# HTTP, so following the redirect is impossible. Disable it for the suite
# rather than changing the production control.
os.environ.setdefault("HTTPS_REDIRECT_ENABLED", "0")
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
os.environ.setdefault("STRIPE_PRICE_ID", "price_dummy")
os.environ.setdefault("STRIPE_TEAM_PRICE_ID", "price_dummy")
os.environ.setdefault("STRIPE_EMBED_PRICE_ID", "price_dummy")
os.environ.setdefault("STRIPE_PREMIUM_ACTION_PRICE_ID", "price_dummy")

# Supabase credentials are deliberately NOT set here. This is the root
# conftest, so anything set at collection time leaks into every suite in the
# run, including the ones that assert an unconfigured deployment falls back
# to a denying client. Those tests set and clear their own environment
# instead, which keeps them order-independent.


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Give the rate limiter fresh state before each test.

    The limiter is a process-global with in-memory sliding windows keyed by
    client identity. Anonymous callers share one bucket (30 requests/60s by
    default), so a suite that makes many requests fills it and a later test
    gets a 429 for a reason unrelated to the behaviour under test. The result
    then depends on collection order instead of on the code.

    The global is replaced rather than cleared because several internal maps
    hold window state, and clearing one leaves the rest pointing at the same
    exhausted windows.
    """
    import app.middleware.security.rate_limit_hardened as rl

    previous = rl._GLOBAL_LIMITER
    rl._GLOBAL_LIMITER = rl.RateLimiter()
    try:
        yield
    finally:
        rl._GLOBAL_LIMITER = previous


def _ensure_module(name):
    """Return a module for `name`, synthesising a stub only if absent.

    The `__import__` is wrapped in `except Exception`, not just `ImportError`.
    Importing a router module transitively imports `app`, and when that raises
    a non-ImportError (for example `RuntimeError: JWT_SECRET_KEY must be set`
    from `app/config.py`) Python discards the half-initialised top-level
    package, so `app` lost its `__path__` and every later
    `from app import <module>` failed with "'app' is not a package".
    """
    if name not in sys.modules:
        try:
            __import__(name)
        except Exception as exc:  # noqa: BLE001 - a failed import must not
            # discard the partially-imported parent package from sys.modules.
            print(f"[conftest] import of {name} failed, stubbing: {exc}")
        if name not in sys.modules:
            mod = types.ModuleType(name)
            mod.__path__ = []
            sys.modules[name] = mod
    return sys.modules[name]


# Importing any router module transitively imports `app`, which reads its
# configuration at import time. The configuration is established first so the
# first import of `app` cannot fail mid-way.
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
try:
    importlib.import_module("app")
except Exception as exc:  # noqa: BLE001 - reported, suite continues
    print(f"[conftest] could not pre-import app: {exc}")


def _set_attr_chain(mod_name, attr_name, value):
    mod = sys.modules.get(mod_name)
    if mod is not None:
        setattr(mod, attr_name, value)


# Create top-level aliases for app subpackages that are imported without the
# 'app.' prefix. Names that also exist as a real top-level package/module under
# 02-Backend (for example `database`) must NOT be aliased: doing so shadows the
# real package and breaks `from database.database import ...`.
_SHADOWED_TOP_LEVEL = {
    os.path.splitext(fn)[0]
    for fn in os.listdir(_backend_root)
    if not fn.startswith(".")
} if os.path.isdir(_backend_root) else set()

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
    # Never shadow a real top-level package/module under the backend root.
    if alias.split(".")[0] in _SHADOWED_TOP_LEVEL:
        continue
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
    module = sys.modules[mod_name]
    # Only a module that has no router of its own - i.e. one synthesised
    # above because the real module does not exist in this tree - gets the
    # mock. Replacing a real module's router unregisters every route the
    # product serves under that prefix, which turns a live endpoint into a
    # 404 that looks like "the feature was never built".
    if getattr(module, "router", None) is None:
        module.router = _mock_router
    if mod_name == "api.routers.jobs_router" and getattr(module, "events_router", None) is None:
        module.events_router = _mock_router

import pytest
from app.database import init_db

# Apply the fixture schema before the app is imported. Several endpoints
# fail with "no such table" otherwise, which reports as a product error
# rather than the environment gap it actually is.
try:
    from tests.schema_fixture import create_schema as _create_schema

    _create_schema()
except Exception as _schema_exc:  # noqa: BLE001 - logged, suite continues
    import logging as _logging

    _logging.getLogger(__name__).warning(
        "fixture.schema unavailable: %s", _schema_exc
    )

try:
    from app.main import app
except Exception:
    from fastapi import FastAPI
    app = FastAPI(title="test")
from fastapi.testclient import TestClient
try:
    from app.database import init_db
except Exception:
    init_db = None
try:
    from app.main import app
    from fastapi.testclient import TestClient
except Exception:
    app = None
    TestClient = None
try:
    import app.billing as billing_module
except Exception:
    billing_module = None

DB_PATH = os.environ.get("ASTROVOX_DB", "test.db")

if app is not None and TestClient is not None:
    # The app installs an IP allowlist that rejects non-IP client hosts, so
    # the transport presents as loopback instead of Starlette's default
    # "testclient" host. The CSRF middleware is satisfied by the api_client
    # fixture below; plain `client` keeps the raw app behaviour.
    client = TestClient(app, client=("127.0.0.1", 50000))
else:
    client = None


@pytest.fixture
def api_client():
    """TestClient that satisfies the CSRF middleware.

    The middleware requires an `X-CSRF-Token` header matching the `csrftoken`
    cookie on every state-changing request. Sending both keeps the security
    control intact while letting the suite exercise POST endpoints.
    """
    from fastapi.testclient import TestClient as _TestClient

    if app is None:
        pytest.skip("app.main could not be imported")

    with _TestClient(app) as c:
        c.headers.update({"X-CSRF-Token": "test-csrf-token"})
        c.cookies.set("csrftoken", "test-csrf-token")
        yield c


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    if init_db is not None:
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
    if billing_module is None:
        yield {}
        return

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

    _patches = [
        patch('app.billing.stripe', mock_stripe),
        patch.object(billing_module, '_STRIPE_CONFIGURED', True),
        patch('openai.OpenAI', return_value=mock_openai_client),
    ]
    # Patches are only applied when their target actually exists. The solve
    # route (`app.routers.solve`) is not present in this tree, so guarding on
    # `sys.modules` alone is not enough: patch() resolves the attribute
    # immediately and raises. Importing the module first and checking for the
    # attribute keeps the fixture from erroring every test in the suite.
    def _safe_patch(target, **kwargs):
        """Return a patch for `target`, or None when it is unavailable."""
        module_name, _, attr = target.rpartition('.')
        module = sys.modules.get(module_name)
        if module is None:
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                return None
        if not hasattr(module, attr):
            return None
        try:
            return patch(target, **kwargs)
        except (AttributeError, ModuleNotFoundError):
            return None

    for _target, _kwargs in (
        ('app.core.moderation.check_moderation', {'return_value': (False, None)}),
        ('app.routers.solve.check_moderation', {'return_value': (False, None)}),
        ('app.routers.solve.ground_answer', {'return_value': ("Mocked answer", False, 0.9)}),
        ('app.core.providers.get_active_providers', {'return_value': []}),
        ('app.main.llm_client.call_llm', {'return_value': {
            "text": "Mocked answer",
            "provider": "test",
            "model": "test-model",
            "tokens": 10,
            "confidence": 0.9,
        }}),
        ('app.main.llm_client.stream_llm', {'return_value': iter([
            {"token": "Mocked", "provider": "test", "model": "test-model"},
            {"token": " answer", "provider": "test", "model": "test-model"},
        ])}),
    ):
        _candidate = _safe_patch(_target, **_kwargs)
        if _candidate is not None:
            _patches.append(_candidate)

    with ExitStack() as stack:
        for p in _patches:
            stack.enter_context(p)

        yield {
            'stripe': mock_stripe,
            'openai': mock_openai_client,
        }

    if original_stripe is not None:
        billing_module.stripe = original_stripe
    else:
        billing_module.stripe = None
