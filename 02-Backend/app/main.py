from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from chat import router as chat_router
from api import router as api_router
from memory import router as memory_router
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="AstrovoxAi Engine",
    version="2.0.0",
    description="Production-grade asynchronous stateless backend for AI chat"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(api_router)
app.include_router(memory_router)

# Health check endpoints
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "astravox-ai-backend",
        "version": "2.0.0"
    }

@app.get("/health/readiness")
async def readiness_check():
    """Kubernetes readiness probe"""
    return {
        "status": "ready",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat() + 'Z'
    }

@app.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {
        "status": "alive",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat() + 'Z'
    }

@app.get("/")
async def root():
    return {
        "message": "🚀 ASTRAVOX PRIME Backend v2.0.0",
        "status": "operational",
        "endpoints": {
            "auth": "/auth/signup, /auth/login, /auth/logout, /auth/reset-password",
            "health": "/health, /health/readiness, /health/liveness",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
