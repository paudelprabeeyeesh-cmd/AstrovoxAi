from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import time
from dotenv import load_dotenv

from app.services.auth.auth import router as auth_router
from app.chat import router as chat_router
from app.storage import router as storage_router
from app.telemetry import router as telemetry_router
from app.terminal import router as terminal_router
from app.services.vector.embeddings_route import router as embeddings_router
from app.api.routers.memory.router import router as memory_engine_router
from app.api.routers.router import router as enterprise_router
from app.enterprise.ws_router import router as ws_router
from app.api.routers.workspace_route import router as workspace_router
from app.api.routers.jobs_router import router as jobs_router, events_router
from app.api.routers.analytics_route import router as analytics_router
from app.api.routers.knowledge_route import router as knowledge_router
from app.api.routers.agent_route import router as agent_router
from app.api.routers.monitoring_route import router as monitoring_router
from app.api.routers.auth.security_route import router as security_router
from app.api.routers.security_management import router as security_management_router
from app.safety_routes import router as safety_router
from app.middleware.security.ip_ua_enforcement import IPEnforcementMiddleware, UserAgentMiddleware
from app.api.routers.admin_route import router as admin_router
from app.api.routers.realtime_route import router as realtime_router
from app.api.routers.dashboard_route import router as dashboard_router
from app.api.v1 import router as api_v1_router
from app.api.routers.platform_route import router as platform_router
from app.api.routers.knowledge_route_v2 import router as knowledge_v2_router
from app.api.routers.realtime_route import tools_router
from app.api.routers.realtime_route import security_router as scan_router
from app.api.routers.agents_route import router as agents_router
from app.api.routers.agents_route import memory_router as memory_v2_router
from app.api.routers.automation_route import router as automation_router
from app.kernel.api import router as kernel_router
from app.aios.api import router as aios_router
from app.api.routers.document_route import router as document_router
from app.performance_route import router as performance_router
from app.middleware.security.security_headers import SecurityHeadersMiddleware
from app.middleware.security.rate_limit_hardened import rate_limit_middleware
from app.middleware import GlobalExceptionMiddleware, InputValidationMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.core.structured_logging import StructuredLoggingMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.shutdown import register_lifecycle_handlers, GracefulShutdownMiddleware
from app.middleware.request_limits import RequestTimeoutMiddleware, PayloadSizeLimitMiddleware
from app.middleware.error_handler import register_error_handlers
from app.middleware.content_negotiation import ContentNegotiationMiddleware
from app.core.cache_enhanced import get_cached_response, cache_response
from app.api.routers.bulk_router import router as bulk_router
from app.api.routers.tasks_router import router as tasks_router
from app.api.routers.webhook_router import router as webhook_router
from app.api.routers.feature_flags_router import router as feature_flags_router
from app.api.routers.admin_metrics_router import router as admin_metrics_router
from app.api.routers.support_router import router as support_router
from app.enterprise.abac_router import router as enterprise_abac_router
from app.enterprise.team_router import router as enterprise_team_router
from app.enterprise.ticket_routing_router import router as enterprise_ticket_routing_router
from app.enterprise.billing_router import router as enterprise_billing_router
from app.enterprise.admin_router import router as enterprise_admin_router
from app.enterprise.sso_router import router as enterprise_sso_router
from app.api.routers.cx_router import router as cx_router
from app.api.routers.search_knowledge_route import router as search_knowledge_router
from app.observability.endpoints import router as observability_router
from app.routers.neural_bci import router as neural_bci_router
from app.multiverse import multiverse_router

load_dotenv()

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="AstravoxAi Engine",
    version="1.0.0",
    description="Production-grade asynchronous stateless backend for AI chat",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Standardized error responses
register_error_handlers(app)

app.middleware("http")(rate_limit_middleware)

# CORS Middleware
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(IPEnforcementMiddleware)
app.add_middleware(UserAgentMiddleware)

# Request logging with correlation id propagation
app.add_middleware(RequestLoggingMiddleware)

# Idempotency key enforcement for state-changing requests
app.add_middleware(IdempotencyMiddleware)

# Request timeout and payload size limits
app.add_middleware(RequestTimeoutMiddleware, timeout_seconds=30.0)
app.add_middleware(PayloadSizeLimitMiddleware, max_bytes=10 * 1024 * 1024)

# Graceful shutdown
app.add_middleware(GracefulShutdownMiddleware, drain_timeout=30.0)
app.add_middleware(ContentNegotiationMiddleware)
register_lifecycle_handlers(app)

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(storage_router)
app.include_router(telemetry_router)
app.include_router(terminal_router)
app.include_router(embeddings_router)
app.include_router(memory_engine_router)
app.include_router(enterprise_router)
app.include_router(enterprise_abac_router)
app.include_router(enterprise_team_router)
app.include_router(enterprise_sso_router)
app.include_router(enterprise_billing_router)
app.include_router(enterprise_ticket_routing_router)
app.include_router(enterprise_admin_router)
app.include_router(ws_router)
app.include_router(workspace_router)
app.include_router(jobs_router)
app.include_router(events_router)
app.include_router(analytics_router)
app.include_router(knowledge_router)
app.include_router(agent_router)
app.include_router(monitoring_router)
app.include_router(security_router)
app.include_router(security_management_router)
app.include_router(safety_router)
app.include_router(admin_router)
app.include_router(realtime_router)
app.include_router(dashboard_router)
app.include_router(api_v1_router)
app.include_router(platform_router)
app.include_router(knowledge_v2_router)
app.include_router(tools_router)
app.include_router(scan_router)
app.include_router(agents_router)
app.include_router(memory_v2_router)
app.include_router(automation_router)
app.include_router(document_router)
app.include_router(performance_router)
app.include_router(kernel_router)
app.include_router(aios_router)
app.include_router(bulk_router)
app.include_router(tasks_router)
app.include_router(webhook_router)
app.include_router(feature_flags_router)
app.include_router(admin_metrics_router)
app.include_router(support_router)
app.include_router(cx_router)
app.include_router(observability_router)
app.include_router(search_knowledge_router)
app.include_router(neural_bci_router)
app.include_router(multiverse_router)


# Prometheus metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request metrics for Prometheus."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    try:
        from app.metrics import track_request
        track_request(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration=duration,
        )
    except Exception:
        pass

    return response


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/health/liveness")
async def liveness():
    return {"status": "alive"}


@app.get("/health/readiness")
async def readiness():
    checks = {}
    try:
        from app.database.database import get_db
        with get_db() as conn:
            conn.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as exc:
        checks["database"] = f"unhealthy: {exc}"

    overall = "ready" if all(v == "healthy" for v in checks.values()) else "not_ready"
    return {"status": overall, "checks": checks}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


@app.on_event("startup")
async def _startup():
    try:
        from app.background_workers import BackgroundWorker
        await BackgroundWorker.start(num_workers=4)
    except Exception:
        pass
    try:
        from app.observability import start_observability
        await start_observability()
    except Exception:
        pass
