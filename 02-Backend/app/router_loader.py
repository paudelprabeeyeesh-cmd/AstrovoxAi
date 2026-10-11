"""Optional router loading (D05-03).

Every subsystem below is loaded through one helper instead of thirty
try/except blocks that install an empty APIRouter on failure. That pattern
made a broken import indistinguishable from a healthy, empty subsystem: a
missing feature vanished with no log line, so a backend advertising "30+
features" could be missing twenty of them at runtime.

This loader:

* logs the failing module, the exception type, and a request-scoped
  correlation id at ERROR level, so the failure is visible and traceable;
* returns a router that reports 503 with a stable code for the affected
  paths, so a caller gets an explicit documented error instead of a 404
  that looks like "route never existed";
* records the failure in a startup summary the readiness probe surfaces.

The behaviour is fail-closed in reporting terms: the app still starts,
because a single broken optional subsystem must not take down auth and
health, but the break is loud.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status

logger = logging.getLogger(__name__)

ROUTER_IMPORT_FAILURES: dict[str, str] = {}


def _correlation_id(request: Optional[Request]) -> str:
    """Per-request id so a failure in one call can be traced in logs."""
    if request is not None and hasattr(request, "state"):
        existing = getattr(request.state, "correlation_id", None)
        if existing:
            return str(existing)
    return uuid.uuid4().hex[:12]


def _broken_router(name: str, module: str, reason: str) -> APIRouter:
    """Router that reports the load failure instead of silently returning 404.

    A catch-all path matches any prefix under the subsystem's mount point,
    so existing callers of a missing router get a 503 with the real reason
    rather than a 404 that looks like "route never existed".
    """
    router = APIRouter()

    def _unavailable(request: Request):
        cid = _correlation_id(request)
        message = (
            f"Subsystem '{name}' is unavailable in this deployment because "
            f"loading '{module}' failed"
        )
        logger.error(
            "router.unavailable subsystem=%s module=%s correlation_id=%s reason=%s",
            name, module, cid, reason,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=message,
        )

    for method in ("get", "post", "put", "patch", "delete"):
        router.api_route(
            "/{sub_path:path}",
            methods=[method.upper()],
            include_in_schema=False,
        )(_unavailable)
    return router


def load_router(name: str, module: str) -> APIRouter:
    """Import ``module`` and return its ``router``.

    On failure, returns the documented-error router and records why, so
    the break is visible and attributable.
    """
    try:
        module_obj = __import__(module, fromlist=["router"])
        router = getattr(module_obj, "router")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - logged with the reason, not swallowed
        reason = f"{type(exc).__name__}: {exc}"
        ROUTER_IMPORT_FAILURES[name] = reason
        logger.error(
            "router.import_failed subsystem=%s module=%s reason=%s",
            name, module, reason,
        )
        return _broken_router(name, module, reason)
    if not isinstance(router, APIRouter):
        reason = f"{module} did not export an APIRouter"
        ROUTER_IMPORT_FAILURES[name] = reason
        logger.error(
            "router.import_invalid subsystem=%s module=%s reason=%s",
            name, module, reason,
        )
        return _broken_router(name, module, reason)
    return router


ROUTER_MODULES = {
    # /memory is served by phase14_memory_router and memory_v2_router; there is
    # no app.memory.router, so mounting the name here only produced a broken
    # router (and, before the loader existed, a silent empty one).
    "storage": ".storage",
    "telemetry": ".telemetry",
    "terminal": ".terminal",
    "embeddings": ".embeddings_route",
    "rag": ".rag.routes",
    "cloud": ".routers.cloud",
    "memory_extended": ".routers.memory_extended",
    "rag_extended": ".routers.rag_extended",
    "memory_consolidation": ".routers.memory_consolidation",
    "enterprise_api": ".routers.enterprise_api",
    "support_api": ".routers.support_api",
    "white_label_api": ".routers.white_label_api",
    "custom_domains_api": ".routers.custom_domains_api",
    "compliance_api": ".routers.compliance_api",
    "security_api": ".routers.security_api",
    "quota_api": ".routers.quota_api",
    "performance": ".routers.performance",
    "scim_api": ".routers.scim_api",
}


def _local(module: str) -> str:
    """Turn ".routers.cloud" into "app.routers.cloud" for direct import."""
    return "app" + module


_LOADED: dict[str, APIRouter] = {}


def load_all_routers() -> dict[str, APIRouter]:
    """Load every optional router, keeping the historical variable names."""
    for name, module in ROUTER_MODULES.items():
        try:
            _LOADED[name] = load_router(name, _local(module))
        except Exception as exc:  # noqa: BLE001
            reason = f"{type(exc).__name__}: {exc}"
            ROUTER_IMPORT_FAILURES[name] = reason
            logger.error(
                "router.load_error subsystem=%s module=%s reason=%s",
                name, module, reason,
            )
    return _LOADED


def router_health() -> dict:
    """Summary for the readiness probe and /health/components."""
    total = len(ROUTER_MODULES)
    failed = len(ROUTER_IMPORT_FAILURES)
    return {
        "routers_total": total,
        "routers_failed": failed,
        "routers_failed_names": sorted(ROUTER_IMPORT_FAILURES),
        "status": "degraded" if failed else "ok",
    }


def bind(globals_dict: dict) -> None:
    """Install each loaded router under its historical module name."""
    for name, router in _LOADED.items():
        global_name = name if name.endswith("_api") else name + "_router"
        globals_dict[global_name] = router
        alt_name = name.replace("_api", "") + "_api_router"
        globals_dict.setdefault(alt_name, router)
        legacy = name + "_api_router"
        globals_dict.setdefault(legacy, router)
