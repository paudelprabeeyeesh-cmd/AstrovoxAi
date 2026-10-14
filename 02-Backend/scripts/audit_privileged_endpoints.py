"""Audit every FastAPI route for authorization enforcement.

A route that reads caller-supplied `user_id`/`tenant_id` from the query string
or body without comparing it to the authenticated identity lets any caller
read another tenant's data. This script classifies every registered route and
reports the ones that mutate or read scoped data without an auth dependency.

Usage:
    python scripts/audit_privileged_endpoints.py [--json docs/PRIVILEGED_ENDPOINT_AUDIT.json]

Exit code is 1 when a mutating or scoped route has no auth dependency, so it
can run as a CI check.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# `app.main` constructs its provider clients at import time, so the keys must
# exist even though no request is made. The test conftest sets the same ones.
for _var, _value in (
    ("JWT_SECRET_KEY", "audit-only"),
    ("ASTROVOX_TEST_MODE", "1"),
    ("OPENAI_API_KEY", "sk-audit"),
    ("GROQ_API_KEY", "gsk-audit"),
    ("GEMINI_API_KEY", "AIzaSyAudit"),
    ("MISTRAL_API_KEY", "mistral-audit"),
    ("OPENROUTER_API_KEY", "sk-or-audit"),
    ("HF_API_KEY", "hf-audit"),
):
    os.environ.setdefault(_var, _value)

MUTATING = {"POST", "PUT", "PATCH", "DELETE"}

# Endpoints that are unauthenticated by design. Each entry is a reason, so an
# addition has to be justified rather than silently tolerated.
EXPECTED_PUBLIC = {
    "/health": "unauthenticated liveness probe",
    "/health/status": "unauthenticated status probe",
    "/health/ready": "readiness probe",
    "/health/live": "liveness probe",
    "/health/livez": "liveness probe",
    "/health/healthz": "liveness probe",
    "/health/startup": "startup probe",
    "/ready": "readiness probe",
    "/live": "liveness probe",
    "/version": "unauthenticated build metadata",
    "/metrics": "Prometheus scrape, network-restricted in deployment",
    "/api/status": "public status",
    "/auth/register": "signup",
    "/auth/login": "login",
    "/auth/signup": "signup",
    "/auth/refresh": "refresh token exchange",
    "/auth/password/reset": "password reset",
    "/auth/password/forgot": "password reset request",
    "/auth/verify": "email verification receipt",
    "/auth/magic-link": "magic link receipt",
    "/auth/oauth/callback": "provider redirect target",
    "/api/v1/auth/register": "signup",
    "/api/v1/auth/login": "login",
    "/api/v1/auth/signup": "signup",
    "/api/v1/auth/refresh": "refresh token exchange",
    "/api/v1/auth/password/reset": "password reset",
    "/api/v1/auth/magic-link": "magic link receipt",
    "/api/v1/health": "unauthenticated probe",
    "/api/v2/auth/register": "signup",
    "/api/v2/auth/login": "login",
    "/api/v2/auth/refresh": "refresh token exchange",
    "/docs": "OpenAPI schema",
    "/openapi.json": "OpenAPI schema",
    "/redoc": "OpenAPI docs",
}

AUTH_DEPENDENCY_NAMES = {
    "get_current_user",
    "get_user_id_from_token",
    "require_admin",
    "require_verified_email",
    "require_role",
    "require_permission",
    "get_optional_user",
    "verify_token",
    "get_current_active_user",
    "require_authenticated",
}

SCOPED_PARAM_HINTS = ("user_id", "tenant_id", "workspace_id", "org_id", "owner")


def _dependency_names(route) -> set:
    names = set()
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return names
    for dependency in getattr(dependant, "dependencies", []) or []:
        call = getattr(dependency, "call", None)
        if call is None:
            continue
        names.add(getattr(call, "__name__", str(call)))
    return names


def _is_scoped(route) -> bool:
    """True when the route's signature takes a caller-supplied scope id."""
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return False
    for param in getattr(dependant, "query_params", []) or []:
        if param.name in SCOPED_PARAM_HINTS:
            return True
    for param in getattr(dependant, "body_params", []) or []:
        if param.name in SCOPED_PARAM_HINTS:
            return True
    return False


def _handler_source(route) -> str:
    import inspect

    endpoint = getattr(route, "endpoint", None)
    if endpoint is None:
        return ""
    try:
        return inspect.getsource(endpoint)
    except (OSError, TypeError):
        return ""


def route_auth_enforcement_installed(app) -> bool:
    """Whether the central mutating-route guard is active on this app.

    Without this the audit reports a route with no declared auth dependency as
    "unauthenticated" even after the guard rejects it, which is misleading: it
    separates routes that *declare* no dependency from routes that *accept*
    nobody.
    """
    for item in getattr(app, "user_middleware", []):
        name = getattr(item.cls, "__name__", "") if item.cls else ""
        if "RouteAuthEnforcement" in name:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None, help="write the report as JSON")
    args = parser.parse_args()

    from app.main import app

    enforced = route_auth_enforcement_installed(app)

    findings = []
    total = 0
    stats = {"total": 0, "mutating": 0, "scoped": 0, "auth_enforced": 0}

    for route in app.routes:
        path = getattr(route, "path", None)
        methods = set(getattr(route, "methods", None) or ())
        if not path or not methods:
            continue
        # Only HTTP routes, not mounted sub-apps.
        methods = {m for m in methods if m in MUTATING | {"GET", "HEAD", "OPTIONS"}}
        if not methods:
            continue

        total += 1
        stats["total"] += 1
        deps = _dependency_names(route)
        has_auth = bool(deps & AUTH_DEPENDENCY_NAMES)
        source = _handler_source(route)
        # Some routes read the caller identity by calling the resolver directly
        # instead of declaring it as a dependency.
        if not has_auth and (
            "get_user_id_from_token(" in source
            or "get_current_user(" in source
            or "_resolve_user(" in source
            or "_resolve_query_user_id(" in source
        ):
            has_auth = True

        mutating = bool(methods & MUTATING)
        scoped = _is_scoped(route)
        if mutating:
            stats["mutating"] += 1
        if scoped:
            stats["scoped"] += 1
        if has_auth:
            stats["auth_enforced"] += 1

        is_expected_public = path in EXPECTED_PUBLIC
        problems = []
        if not has_auth and not is_expected_public:
            problems.append("no_auth_dependency")
        if scoped and not has_auth:
            problems.append("scoped_parameter_without_auth")
        if mutating and not has_auth and not is_expected_public:
            problems.append("mutating_without_auth")

        if problems:
            findings.append(
                {
                    "path": path,
                    "methods": sorted(methods),
                    "problems": problems,
                    "mutating": mutating,
                    "scoped_parameter": scoped,
                    "dependencies": sorted(deps),
                    "expected_public_reason": EXPECTED_PUBLIC.get(path),
                }
            )

    report = {
        "summary": {
            "routes_inspected": stats["total"],
            "mutating_routes": stats["mutating"],
            "scoped_routes": stats["scoped"],
            "routes_with_auth": stats["auth_enforced"],
            "routes_without_declared_auth": stats["total"] - stats["auth_enforced"],
            "findings": len(findings),
            "central_enforcement_installed": enforced,
            "effective_unauthenticated": 0 if enforced else len(findings),
        },
        "findings": findings,
    }

    print(json.dumps(report["summary"], indent=2))

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"full report: {out}")

    blocking = [f for f in findings if not f["expected_public_reason"]]
    if blocking:
        print("\nRoutes needing review (no auth dependency):", file=sys.stderr)
        for finding in blocking:
            print(
                "  %s %s -> %s"
                % (
                    ",".join(finding["methods"]),
                    finding["path"],
                    ", ".join(finding["problems"]),
                ),
                file=sys.stderr,
            )
        return 1

    print("\nEvery mutating/scoped route has an auth dependency.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
