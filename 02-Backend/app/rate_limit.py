import time
import redis

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .database import get_db
from .subscriptions import get_plan_limits
from .auth import get_current_user


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        redis_client = getattr(request.app.state, "redis", None)

        if path == "/auth/login":
            client_ip = request.client.host if request.client else "unknown"
            if self._is_rate_limited(redis_client, f"login:{client_ip}", 5, 60):
                return JSONResponse(status_code=429, content={"detail": "Too many login attempts. Try again later."})

        elif path == "/auth/register":
            client_ip = request.client.host if request.client else "unknown"
            if self._is_rate_limited(redis_client, f"register:{client_ip}", 3, 60):
                return JSONResponse(status_code=429, content={"detail": "Too many registration attempts. Try again later."})

        elif path == "/solve":
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                token = auth.replace("Bearer ", "")
                try:
                    from jose import jwt
                    from app.config import settings
                    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                    if payload.get("type") == "access":
                        user_id = payload.get("sub")
                        plan = "free"
                        with get_db() as conn:
                            row = conn.execute("SELECT plan FROM users WHERE id = ?", (user_id,)).fetchone()
                            if row:
                                plan = row["plan"]
                        limits = get_plan_limits(plan)
                        solve_limit = limits.get("solve_per_minute", 20)
                        if self._is_rate_limited(redis_client, f"solve:{user_id}", solve_limit, 60):
                            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Upgrade to continue."})
                except Exception:
                    pass

        elif path == "/solve/stream":
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                token = auth.replace("Bearer ", "")
                try:
                    from jose import jwt
                    from app.config import settings
                    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                    if payload.get("type") == "access":
                        user_id = payload.get("sub")
                        if self._is_rate_limited(redis_client, f"solve_stream:{user_id}", 10, 60):
                            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})
                except Exception:
                    pass

        if path not in ["/health", "/metrics", "/docs", "/openapi.json", "/ready", "/live"]:
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                token = auth.replace("Bearer ", "")
                try:
                    from jose import jwt
                    from app.config import settings
                    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                    if payload.get("type") != "access":
                        raise HTTPException(status_code=401, detail="Invalid token type")
                    user_id = payload.get("sub")
                except Exception:
                    return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

                client_ip = request.client.host if request.client else "unknown"
                lockout_until = None
                with get_db() as conn:
                    row = conn.execute("SELECT lockout_until FROM login_attempts WHERE ip = ? ORDER BY created_at DESC LIMIT 1", (client_ip,)).fetchone()
                    if row and row["lockout_until"]:
                        lockout_until = row["lockout_until"]
                        if time.strftime("%Y-%m-%dT%H:%M:%S") < lockout_until:
                            return JSONResponse(status_code=429, content={"detail": "Too many failed attempts. Try again later."})

                plan = "free"
                with get_db() as conn:
                    row = conn.execute(
                        "SELECT plan FROM users WHERE id = ?",
                        (user_id,)
                    ).fetchone()
                    if row:
                        plan = row["plan"]
                limits = get_plan_limits(plan)
                today = time.strftime("%Y-%m-%d")
                with get_db() as conn:
                    count = conn.execute(
                        "SELECT COUNT(*) as c FROM usage WHERE user_id = ? AND date(created_at) = ?",
                        (user_id, today),
                    ).fetchone()["c"]
                if count >= limits["requests"]:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": f"Daily limit reached for {plan} plan. Upgrade to continue."}
                    )
        response = await call_next(request)
        return response

    def _is_rate_limited(self, redis_client, key: str, limit: int, window_seconds: int) -> bool:
        if redis_client:
            try:
                now = time.time()
                window_start = now - window_seconds
                member = f"{now}:{key}"
                pipe = redis_client.pipeline(transaction=True)
                pipe.zadd(key, {member: now})
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zcard(key)
                results = pipe.execute()
                count = results[2]
                return count >= limit
            except Exception:
                pass
        return False


def record_failed_login(ip: str):
    with get_db() as conn:
        conn.execute("INSERT INTO login_attempts (id, ip, success, created_at) VALUES (?, ?, 0, ?)",
                     (str(__import__('uuid').uuid4()), ip, time.strftime("%Y-%m-%dT%H:%M:%S")))
        conn.commit()
    one_hour_ago = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 3600))
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) as c FROM login_attempts WHERE ip = ? AND success = 0 AND created_at > ?", (ip, one_hour_ago)).fetchone()["c"]
    if count >= 10:
        lockout_until = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() + 3600))
        with get_db() as conn:
            conn.execute("UPDATE login_attempts SET lockout_until = ? WHERE ip = ?", (lockout_until, ip))
            conn.commit()


def record_successful_login(ip: str):
    with get_db() as conn:
        conn.execute("INSERT INTO login_attempts (id, ip, success, created_at) VALUES (?, ?, 1, ?)",
                     (str(__import__('uuid').uuid4()), ip, time.strftime("%Y-%m-%dT%H:%M:%S")))
        conn.commit()
