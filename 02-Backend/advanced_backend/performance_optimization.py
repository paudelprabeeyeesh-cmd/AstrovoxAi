import bisect
import time
from typing import Any, Callable, Dict, List, Tuple


class QueryOptimizer:
    def __init__(self) -> None:
        self._indexes: Dict[str, List[Tuple[Any, Any]]] = {}

    def create_index(self, table: str, column: str) -> None:
        self._indexes.setdefault(f"{table}.{column}", [])

    def insert(self, table: str, column: str, key: Any, row: Any) -> None:
        idx = self._indexes.setdefault(f"{table}.{column}", [])
        bisect.insort(idx, (key, row))

    def range_scan(self, table: str, column: str, lo: Any, hi: Any) -> List[Any]:
        idx = self._indexes.get(f"{table}.{column}", [])
        if not idx:
            return []
        left = bisect.bisect_left(idx, (lo,))
        right = bisect.bisect_right(idx, (hi,))
        while right < len(idx) and idx[right][0] <= hi:
            right += 1
        return [row for _, row in idx[left:right]]

    def explain(self, table: str, column: str, lo: Any, hi: Any) -> Dict[str, Any]:
        idx = self._indexes.get(f"{table}.{column}")
        return {
            "plan": "INDEX_RANGE_SCAN" if idx else "FULL_SCAN",
            "estimated_rows": len(idx) if idx else 0,
            "index_used": bool(idx),
        }


class MaterializedView:
    def __init__(self, refresh_interval: float = 60.0) -> None:
        self._refresh_interval = refresh_interval
        self._last_refresh = 0.0
        self._data: Any = None

    def refresh(self, compute: Callable[[], Any]) -> None:
        self._data = compute()
        self._last_refresh = time.time()

    def get(self) -> Any:
        return self._data

    def stale(self) -> bool:
        return (time.time() - self._last_refresh) > self._refresh_interval
