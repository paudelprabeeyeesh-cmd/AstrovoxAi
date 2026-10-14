import sys

sys.path.insert(0, ".")

from fastapi.testclient import TestClient

import tests.security.test_route_auth_enforcement as mod
from app.middleware.security.route_auth_enforcement import is_authenticated_route

# Build the same app the fixture builds, then inspect what the middleware sees.
app = mod._build_probe_app() if hasattr(mod, "_build_probe_app") else None

client = TestClient(app) if app else None
print("app built:", app is not None)
if app:
    routes = {getattr(r, "path", None): r for r in app.routes}
    for path, route in routes.items():
        endpoint = getattr(route, "endpoint", None)
        code = getattr(endpoint, "__code__", None)
        print(
            path,
            "->",
            is_authenticated_route(route),
            "co_names:",
            list(code.co_names) if code else None,
        )
