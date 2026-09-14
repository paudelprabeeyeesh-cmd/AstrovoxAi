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
