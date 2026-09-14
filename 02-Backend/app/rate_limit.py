import time

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from .database import get_db
from .subscriptions import get_plan_limits


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path not in ["/health", "/metrics", "/docs", "/openapi.json"]:
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer user-"):
                user_id = auth.replace("Bearer user-", "")
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
                    raise HTTPException(
                        status_code=429,
                        detail=f"Daily limit reached for {plan} plan. Upgrade to continue.",
                    )
        response = await call_next(request)
        return response
