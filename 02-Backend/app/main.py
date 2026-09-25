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
from app.middleware.security.security_headers import SecurityHeadersMiddleware
from app.middleware.security.rate_limit_hardened import rate_limit_middleware
from app.middleware import GlobalExceptionMiddleware, InputValidationMiddleware
from app.core.cache_enhanced import get_cached_response, cache_response

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

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(storage_router)
app.include_router(telemetry_router)
app.include_router(terminal_router)
app.include_router(embeddings_router)
app.include_router(memory_engine_router)
app.include_router(enterprise_router)
app.include_router(ws_router)
app.include_router(workspace_router)
app.include_router(jobs_router)
app.include_router(events_router)
app.include_router(analytics_router)
app.include_router(knowledge_router)
app.include_router(agent_router)
app.include_router(monitoring_router)
app.include_router(security_router)
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
app.include_router(kernel_router)
app.include_router(aios_router)


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
    return {"status": "ready"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
