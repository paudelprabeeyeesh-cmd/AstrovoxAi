import time

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .database import get_db
from .subscriptions import get_plan_limits
from .auth import get_current_user


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path not in ["/health", "/metrics", "/docs", "/openapi.json", "/ready", "/live"]:
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

                # Check brute-force lockout per IP
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
                        "SELECT plan FROM users WHERE id = ?", (user_id,)
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


def record_failed_login(ip: str):
    with get_db() as conn:
        conn.execute("INSERT INTO login_attempts (id, ip, success, created_at) VALUES (?, ?, 0, ?)",
                     (str(__import__('uuid').uuid.uuid4()), ip, time.strftime("%Y-%m-%dT%H:%M:%S")))
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
                     (str(__import__('uuid').uuid.uuid4()), ip, time.strftime("%Y-%m-%dT%H:%M:%S")))
        conn.commit()