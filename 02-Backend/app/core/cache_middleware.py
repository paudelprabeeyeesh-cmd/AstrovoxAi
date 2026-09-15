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


def _get_embedding(text):
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.embeddings.create(input=text, model="text-embedding-3-small")
        return response.data[0].embedding
    except Exception as e:
        logger.warning(f"Embedding lookup failed: {e}")
        return None


def _find_similar_cached_response(redis, embedding, threshold=0.95):
    if not redis or not embedding:
        return None
    try:
        for key in redis.scan_iter(match="cache_emb:*"):
            data = redis.get(key)
            if not data:
                continue
            try:
                entry = json.loads(data)
                cached_embedding = entry.get("embedding")
                if cached_embedding and _cosine_similarity(embedding, cached_embedding) > threshold:
                    return entry.get("body")
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Semantic cache scan failed: {e}")
    return None


def _set_cache_headers(response, path: str):
    if path in ("/health", "/healthz"):
        response.headers["Cache-Control"] = "max-age=0, no-cache"
    elif path == "/metrics":
        response.headers["Cache-Control"] = "max-age=10"
    elif path.startswith("/landing"):
        response.headers["Cache-Control"] = "max-age=3600"


class CacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        cache_key = hashlib.md5(f"{request.url.path}:{request.url.query}".encode()).hexdigest()
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
                _set_cache_headers(response, request.url.path)
                return response
            query_text = request.query_params.get("q") or request.query_params.get("query") or request.query_params.get("prompt")
            if not query_text:
                query_text = str(request.url.query) if request.url.query else None
            embedding = None
            if query_text:
                embedding = _get_embedding(query_text)
                if embedding:
                    similar_body = _find_similar_cached_response(redis, embedding)
                    if similar_body:
                        from fastapi.responses import JSONResponse
                        response = JSONResponse(
                            status_code=200,
                            content=json.loads(similar_body),
                            headers={"X-Cache": "HIT"}
                        )
                        _set_cache_headers(response, request.url.path)
                        return response
        response = await call_next(request)
        if response.status_code == 200 and redis:
            if hasattr(response, "body"):
                body = response.body
                if isinstance(body, bytes):
                    body = body.decode("utf-8")
                redis.set(cache_key, body, ex=300)
                query_text = request.query_params.get("q") or request.query_params.get("query") or request.query_params.get("prompt")
                if not query_text:
                    query_text = str(request.url.query) if request.url.query else None
                if query_text:
                    if not embedding:
                        embedding = _get_embedding(query_text)
                    if embedding:
                        semantic_data = {
                            "body": body,
                            "embedding": embedding,
                            "url": str(request.url)
                        }
                        redis.set(f"cache_emb:{cache_key}", json.dumps(semantic_data), ex=300)
        response.headers["X-Cache"] = "MISS"
        _set_cache_headers(response, request.url.path)
        return response
