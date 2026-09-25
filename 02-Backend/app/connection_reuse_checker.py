"""Connection reuse checker."""

import logging
import threading
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger("astrovox.connection_reuse")


class ConnectionReuseChecker:
    """Track and verify database connection reuse."""

    def __init__(self) -> None:
        self._connections: Dict[str, Dict[str, Any]] = {}
        self._reuse_counts: Dict[str, int] = defaultdict(int)
        self._leaked: Set[str] = set()
        self._lock = threading.Lock()

    def register_connection(self, conn_id: str, connection: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._connections[conn_id] = {
                "connection": connection,
                "created_at": __import__("time").time(),
                "metadata": metadata or {},
            }

    def release_connection(self, conn_id: str) -> None:
        with self._lock:
            if conn_id in self._connections:
                self._reuse_counts[conn_id] += 1
                del self._connections[conn_id]

    def check_leaks(self) -> List[Dict[str, Any]]:
        with self._lock:
            now = __import__("time").time()
            leaks = []
            for conn_id, info in self._connections.items():
                age = now - info["created_at"]
                if age > 300:
                    self._leaked.add(conn_id)
                    leaks.append({
                        "conn_id": conn_id,
                        "age_seconds": age,
                        "metadata": info["metadata"],
                    })
            return leaks

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": len(self._connections),
                "leaked": len(self._leaked),
                "reuse_counts": dict(self._reuse_counts),
                "total_created": len(self._connections) + sum(self._reuse_counts.values()),
            }

    def get_active_connections(self) -> List[str]:
        with self._lock:
            return list(self._connections.keys())

    def clear(self) -> None:
        with self._lock:
            self._connections.clear()
            self._reuse_counts.clear()
            self._leaked.clear()


connection_reuse_checker = ConnectionReuseChecker()
