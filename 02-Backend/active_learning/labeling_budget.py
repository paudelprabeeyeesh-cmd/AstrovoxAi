from typing import List, Dict, Any, Optional
from datetime import datetime


class LabelingBudget:
    def __init__(self, total_budget: int):
        if total_budget <= 0:
            raise ValueError("Budget must be a positive integer")
        self.total_budget = total_budget
        self._spent = 0
        self._records: List[Dict[str, Any]] = []

    def consume(self, n: int = 1) -> bool:
        if self._spent + n > self.total_budget:
            return False
        self._spent += n
        self._records.append(
            {
                "amount": n,
                "timestamp": datetime.utcnow().isoformat(),
                "cumulative": self._spent,
            }
        )
        return True

    def remaining(self) -> int:
        return self.total_budget - self._spent

    def spent(self) -> int:
        return self._spent

    def utilization(self) -> float:
        return self._spent / self.total_budget if self.total_budget > 0 else 0.0

    def is_exhausted(self) -> bool:
        return self._spent >= self.total_budget

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._records)

    def reset(self) -> None:
        self._spent = 0
        self._records = []

    def __repr__(self) -> str:
        return (
            f"LabelingBudget(total={self.total_budget}, "
            f"spent={self._spent}, remaining={self.remaining()})"
        )
