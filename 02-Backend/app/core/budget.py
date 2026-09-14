from typing import Optional, Tuple, List
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class CostCircuitBreaker:
    def __init__(self):
        self.user_costs = {}
        self.global_cost_today = 0.0
    
    def check_user_cost(self, user_id: str) -> tuple[bool, Optional[str]]:
        today = self._get_today()
        key = f"{user_id}:{today}"
        cost = self.user_costs.get(key, 0.0)
        
        if cost >= settings.PER_USER_DAILY_CAP_USD:
            logger.warning(f"User {user_id} exceeded daily cap: ${cost}")
            return False, f"Daily cost cap reached: ${settings.PER_USER_DAILY_CAP_USD}"
        return True, None
    
    def check_global_cost(self) -> tuple[bool, Optional[str]]:
        if self.global_cost_today >= settings.DAILY_BUDGET_USD:
            logger.warning(f"Global daily budget exceeded: ${self.global_cost_today}")
            return False, f"Daily budget exceeded: ${settings.DAILY_BUDGET_USD}"
        return True, None
    
    def record_cost(self, user_id: str, cost: float):
        today = self._get_today()
        key = f"{user_id}:{today}"
        self.user_costs[key] = self.user_costs.get(key, 0.0) + cost
        self.global_cost_today += cost
    
    def _get_today(self) -> str:
        from datetime import datetime
        return datetime.utcnow().date().isoformat()


cost_circuit_breaker = CostCircuitBreaker()

