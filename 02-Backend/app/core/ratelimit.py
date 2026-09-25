import logging
import time

logger = logging.getLogger(__name__)


class PerUserRateLimiter:
    def __init__(self):
        self.user_usage = {}

    def check_limit(self, user_id: str, plan: str = "free") -> tuple[bool, dict]:
        limits = {
            "free": {"burst": 10, "sustained": 10},
            "pro": {"burst": 100, "sustained": 1000},
            "team": {"burst": 500, "sustained": 10000},
            "enterprise": {"burst": 1000, "sustained": 100000},
        }

        limit = limits.get(plan, limits["free"])
        now = time.time()
        today_start = int(now // 86400) * 86400

        if user_id not in self.user_usage:
            self.user_usage[user_id] = {
                "day_start": today_start,
                "requests": 0,
                "burst_requests": 0,
            }

        user_data = self.user_usage[user_id]

        if user_data["day_start"] != today_start:
            user_data["day_start"] = today_start
            user_data["requests"] = 0
            user_data["burst_requests"] = 0

        user_data["requests"] += 1
        user_data["burst_requests"] += 1

        if user_data["requests"] > limit["sustained"]:
            logger.warning(f"User {user_id} exceeded sustained limit")
            return False, {
                "reason": "daily_limit_exceeded",
                "limit": limit["sustained"],
            }

        if user_data["burst_requests"] > limit["burst"]:
            logger.warning(f"User {user_id} exceeded burst limit")
            return False, {"reason": "burst_limit_exceeded", "limit": limit["burst"]}

        return True, {"remaining": limit["sustained"] - user_data["requests"]}


rate_limiter = PerUserRateLimiter()
