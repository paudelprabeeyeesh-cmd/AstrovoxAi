from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
import os
from dotenv import load_dotenv

from .auth import router as auth_router
from .chat import router as chat_router
from .api import router as api_router
from .memory_router import router as memory_router
from .intelligence_router import router as intelligence_router
from .security import RequestIDMiddleware, SecurityHeadersMiddleware

load_dotenv()

app = FastAPI(
    title="AstrovoxAi Engine",
    version="2.0.0",
    description="Production-grade asynchronous stateless backend for AI chat",
)

# Keep rate limiting at the API edge. Redis storage should replace the in-memory
# default before running multiple workers or replicas in production.
rate_limit = os.getenv("RATE_LIMIT", "120/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[rate_limit])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

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

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(api_router)
app.include_router(memory_router)
app.include_router(intelligence_router)


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
