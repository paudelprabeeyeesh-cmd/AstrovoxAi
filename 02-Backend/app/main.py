from datetime import datetime, timezone
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
from dotenv import load_dotenv

from .auth import router as auth_router
from .chat import router as chat_router
from .api import router as api_router
from .memory import router as memory_router
from .storage import router as storage_router
from .telemetry import router as telemetry_router
from .terminal import router as terminal_router
from .embedding.router import router as embedding_router
from .memory_engine.router import router as memory_engine_router
from .enterprise.router import router as enterprise_router
from .enterprise.ws_router import router as ws_router
from .jobs_router import router as jobs_router, events_router
from .analytics_route import router as analytics_router
from .knowledge_route import router as knowledge_router
from .agent_route import router as agent_router
from .monitoring_route import router as monitoring_router
from .security_route import router as security_router
from .admin_route import router as admin_router
from .realtime_route import router as realtime_router
from .dashboard_route import router as dashboard_router
from .api_v1 import router as api_v1_router
from .platform_route import router as platform_router
from .realtime_route import tools_router
from .realtime_route import security_router as scan_router
from .agents_route import router as agents_router
from .agents_route import memory_router as memory_v2_router
from .security_headers import SecurityHeadersMiddleware
from .rate_limit import rate_limit_middleware
from .middleware import GlobalExceptionMiddleware, InputValidationMiddleware

load_dotenv()

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="AstrovoxAi Engine",
    version="2.0.0",
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
app.include_router(api_router)
app.include_router(memory_router)
app.include_router(storage_router)
app.include_router(telemetry_router)
app.include_router(terminal_router)
app.include_router(embedding_router)
app.include_router(memory_engine_router)
app.include_router(enterprise_router)
app.include_router(ws_router)
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
app.include_router(tools_router)
app.include_router(scan_router)
app.include_router(agents_router)
app.include_router(memory_v2_router)


# Prometheus metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request metrics for Prometheus."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    try:
        from .metrics import track_request
        track_request(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            duration=duration
        )
    except Exception:
        pass

    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    return response


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    try:
        from .metrics import get_metrics, CONTENT_TYPE_LATEST
        return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return Response(
            content=b"# Prometheus client not installed\n",
            media_type="text/plain"
        )


# Health check endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "astravox-ai-backend", "version": "2.0.0"}


@app.get("/health/readiness")
async def readiness_check():
    """Kubernetes readiness probe"""
    return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/")
async def root():
    return {
        "message": "🚀 ASTRAVOX PRIME Backend v2.0.0",
        "status": "operational",
        "endpoints": {
            "auth": "/auth/signup, /auth/login, /auth/logout, /auth/reset-password",
            "health": "/health, /health/readiness, /health/liveness",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
