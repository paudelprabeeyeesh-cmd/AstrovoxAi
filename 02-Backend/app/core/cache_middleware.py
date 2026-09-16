import hashlib
import json
import math
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings

logger = logging.getLogger(__name__)


def _cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def _get_embedding(text):
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding
    except Exception as e:
        logger.warning(f"Embedding lookup failed: {e}")
        return None


async def _find_similar_cached_response(redis, embedding, threshold=0.95):
    if not redis or not embedding:
        return None
    # Semantic cache disabled temporarily
    return None


def _set_cache_headers(response, path: str):
    if path in ("/health", "/healthz"):
        response.headers["Cache-Control"] = "max-age=0, no-cache"
    elif path == "/metrics":
        response.headers["Cache-Control"] = "max-age=10"
    elif path.startswith("/landing"):
        response.headers["Cache-Control"] = "max-age=3600"


def _get_user_id(request):
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth.replace("Bearer ", "")
        try:
            from jose import jwt
            from app.config import settings
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") == "access":
                return str(payload.get("sub", "anonymous"))
        except Exception:
            pass
    return "anonymous"


class CacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        user_id = _get_user_id(request)
        path = request.url.path
        query = request.url.query
        cache_version = getattr(settings, "CACHE_VERSION", "v1")
        cache_key = f"{user_id}:{request.method}:{path}:{query}"
        cache_key = f"cache:{cache_version}:{hashlib.md5(cache_key.encode()).hexdigest()}"
        if request.method != "GET":
            response = await call_next(request)
            return response
        redis = getattr(request.app.state, "redis", None)
        if redis:
            cached = redis.get(cache_key)
            if cached:
                from fastapi.responses import JSONResponse
                response = JSONResponse(
                    status_code=200,
                    content=json.loads(cached),
                    headers={"X-Cache": "HIT"}
                )
                _set_cache_headers(response, path)
                return response
            query_text = request.query_params.get("q") or request.query_params.get("query") or request.query_params.get("prompt")
            if not query_text:
                query_text = str(request.url.query) if request.url.query else None
            # Semantic cache disabled temporarily
        response = await call_next(request)
        if response.status_code == 200 and redis:
            if hasattr(response, "body"):
                body = response.body
                if isinstance(body, bytes):
                    body = body.decode("utf-8")
                redis.set(cache_key, body, ex=300)
        response.headers["X-Cache"] = "MISS"
        _set_cache_headers(response, path)
        return response
