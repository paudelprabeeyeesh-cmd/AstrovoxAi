"""Production-ready FastAPI inference server for AstrovoxAI."""

import os
import sys
import time
import uuid
import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from .metrics import (
    request_count,
    request_duration,
    model_load_time,
    model_memory_usage,
    model_queue_size,
    token_count,
    active_requests,
    error_count,
    get_metrics_response,
)
from .health import HealthChecker, HealthStatus
from .logging import setup_logging, get_logger, request_id_var, log_request, log_response, log_error

# Configure logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

# ============================================================================
# Configuration
# ============================================================================


class Settings:
    """Application settings with environment variable fallbacks."""

    def __init__(self):
        self.app_name = os.getenv("APP_NAME", "AstrovoxAI Inference")
        self.version = os.getenv("APP_VERSION", "1.0.0")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.api_key = os.getenv("API_KEY", "")
        self.rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
        self.request_timeout = float(os.getenv("REQUEST_TIMEOUT", "30.0"))
        self.max_request_size = int(os.getenv("MAX_REQUEST_SIZE", "10485760"))  # 10MB
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        self.model_path = os.getenv("MODEL_PATH", "")
        self.device = os.getenv("DEVICE", "auto")
        self.workers = int(os.getenv("WORKERS", "1"))
        self.model_config_path = os.getenv(
            "MODEL_CONFIG_PATH",
            os.path.join(os.path.dirname(__file__), "..", "models", "llm", "configs", "config_4b.yaml"),
        )
        self.model_checkpoint_path = os.getenv(
            "MODEL_CHECKPOINT_PATH",
            os.path.join(os.path.dirname(__file__), "..", "models", "llm", "model.pt"),
        )
        self.tokenizer_path = os.getenv(
            "TOKENIZER_PATH",
            os.path.join(os.path.dirname(__file__), "..", "models", "llm", "tokenizer.json"),
        )


settings = Settings()

# ============================================================================
# Request/Response Models
# ============================================================================


class CompletionRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=65536)
    max_tokens: int = Field(default=100, ge=1, le=4096)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    top_k: Optional[int] = Field(default=None, ge=0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0)
    stop: Optional[List[str]] = None
    stream: bool = False


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1)
    max_tokens: int = Field(default=100, ge=1, le=4096)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    top_k: Optional[int] = Field(default=None, ge=0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0)
    stop: Optional[List[str]] = None
    stream: bool = False


class BatchRequest(BaseModel):
    prompts: List[str] = Field(..., min_length=1, max_length=100)
    max_tokens: int = Field(default=100, ge=1, le=4096)
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    top_k: Optional[int] = Field(default=None, ge=0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0)


# ============================================================================
# Rate Limiting (with fallback)
# ============================================================================


class RateLimiter:
    """Simple in-memory rate limiter with fallback when slowapi is unavailable."""

    def __init__(self, requests: int = 100, window: int = 60):
        self.requests = requests
        self.window = window
        self._requests: Dict[str, List[float]] = {}
        self._enabled = True

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def is_allowed(self, client_id: str) -> bool:
        if not self._enabled:
            return True

        now = time.time()
        if client_id not in self._requests:
            self._requests[client_id] = []

        # Clean old requests
        self._requests[client_id] = [
            t for t in self._requests[client_id] if now - t < self.window
        ]

        if len(self._requests[client_id]) >= self.requests:
            return False

        self._requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        if not self._enabled:
            return self.requests

        now = time.time()
        if client_id not in self._requests:
            return self.requests

        self._requests[client_id] = [
            t for t in self._requests[client_id] if now - t < self.window
        ]
        return max(0, self.requests - len(self._requests[client_id]))


_rate_limiter = RateLimiter(
    requests=settings.rate_limit_requests,
    window=settings.rate_limit_window,
)


async def check_rate_limit(request: Request):
    """Check rate limit for the request."""
    if not settings.rate_limit_enabled:
        return

    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(settings.rate_limit_window)},
        )


# ============================================================================
# Authentication (with fallback)
# ============================================================================


async def verify_api_key(request: Request):
    """Verify API key with fallback to disabled mode."""
    if not settings.api_key:
        # No API key configured, allow all requests
        return

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ")[1]
    if token != settings.api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )


# ============================================================================
# Inference Engine (with fallback)
# ============================================================================


class InferenceEngine:
    """Inference engine with graceful fallback."""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None
        self.initialized = False
        self.queue_size = 0
        self._load_error: Optional[str] = None

    async def initialize(self):
        """Initialize the inference engine."""
        if self.initialized:
            return

        try:
            logger.info("Initializing inference engine...")
            start_time = time.time()

            import torch

            # Import here to avoid circular imports
            from models.llm.model.model import LLM
            from models.llm.tokenizer.train_tokenizer import load_tokenizer
            from models.llm.utils.helpers import load_config, get_device, set_cpu_threads

            # Load config
            config = {}
            if os.path.exists(settings.model_config_path):
                config = load_config(settings.model_config_path) or {}

            # Determine device
            dev = settings.device
            if dev == "auto":
                dev = get_device()
            if dev == "cpu":
                set_cpu_threads(min(4, os.cpu_count() or 2))

            device = torch.device(dev)

            # Determine dtype
            dtype = torch.float32
            if dev == "cuda" and config.get("mixed_precision") == "fp16":
                dtype = torch.float16
            elif config.get("mixed_precision") == "bf16" and dev != "cuda":
                dtype = torch.bfloat16

            # Load model
            model = LLM(config, device=device, dtype=dtype)

            # Load checkpoint
            if os.path.exists(settings.model_checkpoint_path):
                model.load_state_dict(
                    torch.load(
                        settings.model_checkpoint_path,
                        map_location=dev,
                        weights_only=True,
                    )
                )

            # Load tokenizer
            tokenizer = load_tokenizer(settings.tokenizer_path)

            self.model = model
            self.tokenizer = tokenizer
            self.device = device
            self.initialized = True
            self._load_error = None

            load_time = time.time() - start_time
            model_load_time.set(load_time)

            logger.info(
                "Model loaded successfully",
                extra={
                    "model_event": "loaded",
                    "model_details": {
                        "device": str(device),
                        "dtype": str(dtype),
                        "load_time_s": round(load_time, 2),
                        "num_layers": getattr(model, "num_hidden_layers", "unknown"),
                        "hidden_size": getattr(model, "hidden_size", "unknown"),
                    },
                },
            )

            # Update memory metrics
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    mem_allocated = torch.cuda.memory_allocated(i)
                    mem_total = torch.cuda.get_device_properties(i).total_memory
                    model_memory_usage.set(mem_allocated)
                    gpu_memory_used.labels(device=str(i)).set(mem_allocated)
                    gpu_memory_total.labels(device=str(i)).set(mem_total)

        except Exception as e:
            self.initialized = False
            self._load_error = str(e)
            logger.error(f"Failed to initialize inference engine: {e}", exc_info=True)

    def generate(self, prompt: str, max_tokens: int = 100, temperature: float = 1.0) -> Dict[str, Any]:
        """Generate text from prompt."""
        if not self.initialized:
            raise HTTPException(status_code=503, detail="Model not initialized")

        self.queue_size += 1
        model_queue_size.set(self.queue_size)

        try:
            from models.llm.inference.engine import InferenceEngine as Engine, SamplingParams

            engine = Engine(self.model, self.tokenizer, self.device)
            params = SamplingParams(
                max_new_tokens=max_tokens,
                temperature=temperature,
            )
            output = engine.generate(prompt, params)

            token_count.labels("prompt").inc(output.prompt_tokens)
            token_count.labels("completion").inc(output.num_tokens)

            return {
                "text": output.text,
                "prompt_tokens": output.prompt_tokens,
                "completion_tokens": output.num_tokens,
                "total_tokens": output.prompt_tokens + output.num_tokens,
                "finish_reason": output.finish_reason,
                "latency_ms": output.latency_ms,
            }
        finally:
            self.queue_size = max(0, self.queue_size - 1)
            model_queue_size.set(self.queue_size)

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        if not self.initialized or not self.model:
            return {
                "status": "not_loaded",
                "error": self._load_error,
            }

        info: Dict[str, Any] = {
            "status": "loaded",
            "model_type": type(self.model).__name__,
            "device": str(self.device),
            "num_layers": getattr(self.model, "num_hidden_layers", "unknown"),
            "hidden_size": getattr(self.model, "hidden_size", "unknown"),
            "num_attention_heads": getattr(self.model, "num_attention_heads", "unknown"),
            "vocab_size": getattr(self.model, "vocab_size", "unknown"),
        }

        if torch.cuda.is_available():
            info["cuda_available"] = True
            info["cuda_device_count"] = torch.cuda.device_count()
            info["cuda_device_name"] = torch.cuda.get_device_name(0)
        else:
            info["cuda_available"] = False

        return info


# Global engine instance
engine = InferenceEngine()

# ============================================================================
# Middleware
# ============================================================================


class RequestIDMiddleware:
    """Add request ID to each request."""

    async def __call__(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimeoutMiddleware:
    """Add timeout handling for requests."""

    def __init__(self, app: Any, timeout: float = 30.0):
        self.app = app
        self.timeout = timeout

    async def __call__(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {request.url.path}")
            raise HTTPException(status_code=504, detail="Request timeout")


class RequestLoggingMiddleware:
    """Log all requests."""

    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        active_requests.inc()

        try:
            log_request(logger, {
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "content_length": request.headers.get("content-length"),
            })

            response = await call_next(request)

            duration_ms = (time.time() - start_time) * 1000
            log_response(logger, {
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            })

            request_count.labels(
                endpoint=request.url.path,
                method=request.method,
                status=response.status_code,
            ).inc()
            request_duration.labels(
                endpoint=request.url.path,
                method=request.method,
            ).observe(duration_ms / 1000)

            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(logger, {
                "message": str(e),
                "endpoint": request.url.path,
                "method": request.method,
                "duration_ms": duration_ms,
                "exc_info": True,
            })
            error_count.labels(
                error_type=type(e).__name__,
                endpoint=request.url.path,
            ).inc()
            raise
        finally:
            active_requests.dec()


class GracefulShutdownMiddleware:
    """Handle graceful shutdown."""

    def __init__(self, app: Any, drain_timeout: float = 30.0):
        self.app = app
        self.drain_timeout = drain_timeout
        self._shutting_down = False

    async def __call__(self, request: Request, call_next):
        if self._shutting_down:
            raise HTTPException(status_code=503, detail="Server is shutting down")
        return await call_next(request)

    def shutdown(self):
        """Initiate graceful shutdown."""
        self._shutting_down = True
        logger.info("Graceful shutdown initiated")


# ============================================================================
# Application Lifecycle
# ============================================================================


async def startup():
    """Application startup handler."""
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    await engine.initialize()


async def shutdown():
    """Application shutdown handler."""
    logger.info("Shutting down inference server...")
    # Cleanup resources
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Production-ready LLM inference API for AstrovoxAI",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.state.startup_complete = False

# Add startup event
@app.on_event("startup")
async def on_startup():
    await startup()
    app.state.startup_complete = True


# Add shutdown event
@app.on_event("shutdown")
async def on_shutdown():
    await shutdown()


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=86400,
)

# Custom middleware (order matters)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TimeoutMiddleware, timeout=settings.request_timeout)

# Initialize graceful shutdown handler
graceful_shutdown = GracefulShutdownMiddleware(app, drain_timeout=30.0)


# ============================================================================
# Routes
# ============================================================================


@app.get("/health")
async def health():
    """Basic health check."""
    return {
        "status": "ok",
        "version": settings.version,
        "model_initialized": engine.initialized,
    }


@app.get("/health/ready")
async def health_ready():
    """Readiness check with detailed health status."""
    checker = HealthChecker(engine=engine)
    return await checker.run_all_checks()


@app.get("/health/live")
async def health_live():
    """Liveness check."""
    return {"status": "alive"}


@app.get("/health/model")
async def health_model():
    """Check model status."""
    return engine.get_model_info()


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics_response()


@app.post("/v1/completions")
async def completions(
    request: CompletionRequest,
    req: Request,
    _: None = Depends(verify_api_key),
    __: None = Depends(check_rate_limit),
):
    """Text completion endpoint."""
    if not engine.initialized:
        raise HTTPException(status_code=503, detail="Model not initialized")

    try:
        result = engine.generate(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        return JSONResponse(content=result)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, {
            "message": f"Completion error: {e}",
            "endpoint": "/v1/completions",
            "method": "POST",
            "exc_info": True,
        })
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    req: Request,
    _: None = Depends(verify_api_key),
    __: None = Depends(check_rate_limit),
):
    """Chat completion endpoint."""
    if not engine.initialized:
        raise HTTPException(status_code=503, detail="Model not initialized")

    try:
        prompt = "\n".join(f"{m.role}: {m.content}" for m in request.messages)
        result = engine.generate(
            prompt=prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        return JSONResponse(
            content={
                "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "astrovox-chat",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result["text"],
                        },
                        "finish_reason": result["finish_reason"],
                    }
                ],
                "usage": {
                    "prompt_tokens": result["prompt_tokens"],
                    "completion_tokens": result["completion_tokens"],
                    "total_tokens": result["total_tokens"],
                },
            }
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, {
            "message": f"Chat completion error: {e}",
            "endpoint": "/v1/chat/completions",
            "method": "POST",
            "exc_info": True,
        })
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/batch")
async def batch_completions(
    request: BatchRequest,
    req: Request,
    _: None = Depends(verify_api_key),
    __: None = Depends(check_rate_limit),
):
    """Batch completion endpoint."""
    if not engine.initialized:
        raise HTTPException(status_code=503, detail="Model not initialized")

    try:
        results = []
        for prompt in request.prompts:
            result = engine.generate(
                prompt=prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            results.append(result)
        return JSONResponse(content={"results": results})
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, {
            "message": f"Batch completion error: {e}",
            "endpoint": "/v1/batch",
            "method": "POST",
            "exc_info": True,
        })
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "inference.app:app",
        host="0.0.0.0",
        port=8000,
        workers=settings.workers,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
    )
