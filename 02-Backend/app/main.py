from datetime import datetime, timezone
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
from dotenv import load_dotenv

from .core.logging_config import configure_logging, RequestLoggingMiddleware

from .auth import router as auth_router
from .audit import router as audit_router
from .chat import router as chat_router
from .secrets import router as secrets_router
from .routers.models_api import router as models_api_router
from .routers.memory_controls import router as memory_controls_router
from .routers.safety_api import router as safety_api_router
from .security_headers import SecurityHeadersMiddleware
from .rate_limit import rate_limit_middleware
from .health import health_service
from .dashboard import get_dashboard

try:
    from .memory import router as memory_router
except Exception as _e:  # noqa: BLE001
    from fastapi import APIRouter
    memory_router = APIRouter()

try:
    from .storage import router as storage_router
except Exception as _e:  # noqa: BLE001
    from fastapi import APIRouter
    storage_router = APIRouter()

try:
    from .telemetry import router as telemetry_router
except Exception as _e:  # noqa: BLE001
    from fastapi import APIRouter
    telemetry_router = APIRouter()

try:
    from .terminal import router as terminal_router
except Exception as _e:  # noqa: BLE001
    from fastapi import APIRouter
    terminal_router = APIRouter()

try:
    from .embeddings_route import router as embeddings_router
except Exception as _e:  # noqa: BLE001
    from fastapi import APIRouter
    embeddings_router = APIRouter()

load_dotenv()

configure_logging()

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
# Origins are configurable via the ALLOWED_ORIGINS env var (comma-separated).
# A wildcard "*" together with allow_credentials=True is rejected by browsers,
# so we default to the local dev frontend instead.
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
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(secrets_router)
app.include_router(storage_router)
app.include_router(telemetry_router)
app.include_router(terminal_router)
app.include_router(embeddings_router)
app.include_router(models_api_router)
app.include_router(memory_controls_router)
app.include_router(safety_api_router)


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
    except Exception as _e:  # noqa: BLE001
        pass

    # Add performance headers
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
    health_service.app = app
    result = health_service.get_overall_health()
    status_code = 200 if result["status"] == "healthy" else 503
    return Response(content=__import__("json").dumps(result), status_code=status_code, media_type="application/json")


@app.get("/healthz")
async def healthz():
    return "ok"


@app.get("/health/readiness")
async def readiness_check():
    """Kubernetes readiness probe - checks dependencies."""
    health_service.app = app
    result = health_service.get_overall_health()
    status_code = 200 if result["status"] in ("healthy", "degraded") else 503
    payload = {
        "status": result["status"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return Response(content=__import__("json").dumps(payload), status_code=status_code, media_type="application/json")


@app.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe - process is alive."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/startup")
async def startup_check():
    """Kubernetes startup probe - application has finished initializing."""
    health_service.app = app
    is_healthy = health_service.is_healthy()
    status_code = 200 if is_healthy else 503
    payload = {
        "status": "started" if is_healthy else "starting",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return Response(content=__import__("json").dumps(payload), status_code=status_code, media_type="application/json")


@app.get("/health/components")
async def components_health():
    """Detailed per-component health breakdown."""
    health_service.app = app
    result = health_service.get_overall_health()
    return result


@app.get("/health/history")
async def health_history():
    """Recent health check history."""
    return {
        "history": health_service.history()[-20:],
        "count": len(health_service.history()),
    }


@app.get("/dashboard")
async def dashboard():
    """Monitoring dashboard payload with panels, health, and metrics."""
    import json as _json
    payload = get_dashboard(app=app)
    return Response(
        content=_json.dumps(payload, default=str),
        media_type="application/json",
    )


@app.get("/")
async def root():
    return {
        "message": "🚀 ASTRAVOX PRIME Backend v2.0.0",
        "status": "operational",
        "endpoints": {
            "auth": "/auth/signup, /auth/login, /auth/logout, /auth/reset-password",
            "health": "/health, /health/readiness, /health/liveness, /health/startup, /health/components, /health/history",
            "dashboard": "/dashboard",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
