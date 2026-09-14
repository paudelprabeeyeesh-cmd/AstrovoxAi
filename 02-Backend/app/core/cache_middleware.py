
import hashlib
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings

class CacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method != "GET":
            return await call_next(request)
        
        cache_key = hashlib.md5(f"{request.url.path}:{request.url.query}".encode()).hexdigest()
        
        # Try to get from cache
        if hasattr(request.app.state, "redis") and request.app.state.redis:
            cached = request.app.state.redis.get(cache_key)
            if cached:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=200,
                    content=json.loads(cached),
                    headers={"X-Cache": "HIT"}
                )
        
        response = await call_next(request)
        
        # Cache successful GET responses
        if response.status_code == 200 and hasattr(request.app.state, "redis") and request.app.state.redis:
            if hasattr(response, "body"):
                body = response.body
                if isinstance(body, bytes):
                    body = body.decode("utf-8")
                request.app.state.redis.set(cache_key, body, ex=300)
        
        response.headers["X-Cache"] = "MISS"
        return response
