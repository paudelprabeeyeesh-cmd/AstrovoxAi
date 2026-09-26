"""User-Agent analytics and blocking rules.

Tracks User-Agent fingerprints, detects known bots/scrapers, and
maintains a blocklist of suspicious or abusive clients.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Set

logger = logging.getLogger(__name__)

KNOWN_BOTS = re.compile(
    r"(?i)(bot|spider|crawler|scraper|curl|wget|python-requests|go-http|"
    r"java|httpclient|axios|okhttp|postman|scanner|nikto|sqlmap|nmap)"
)


@dataclass
class UAStats:
    count: int = 0
    blocked: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0


class UserAgentAnalyzer:
    """Analyzes and enforces User-Agent rules."""

    def __init__(self, max_history: int = 10000) -> None:
        self._stats: Dict[str, UAStats] = {}
        self._blocked: Set[str] = set()
        self._history: Deque[tuple[str, float]] = deque(maxlen=max_history)
        self._lock = threading.Lock()

    def record(self, user_agent: str, ip: str = "") -> tuple[bool, Optional[str]]:
        if not user_agent or not user_agent.strip():
            return False, "missing_user_agent"

        ua = user_agent.strip()

        with self._lock:
            if ua in self._blocked:
                return False, "blocked_user_agent"

            if KNOWN_BOTS.search(ua):
                self._blocked.add(ua)
                logger.info("Blocked bot User-Agent: %s", ua)
                return False, "blocked_bot"

            now = time.time()
            self._history.append((ua, now))
            stats = self._stats.setdefault(ua, UAStats())
            stats.count += 1
            stats.last_seen = now
            if stats.first_seen == 0.0:
                stats.first_seen = now

        return True, None

    def block(self, user_agent: str) -> None:
        with self._lock:
            self._blocked.add(user_agent.strip())

    def unblock(self, user_agent: str) -> None:
        with self._lock:
            self._blocked.discard(user_agent.strip())

    def stats(self) -> Dict[str, Dict]:
        with self._lock:
            return {
                ua: {
                    "count": s.count,
                    "blocked": s.blocked,
                    "first_seen": s.first_seen,
                    "last_seen": s.last_seen,
                }
                for ua, s in self._stats.items()
            }

    def blocked_agents(self) -> list[str]:
        with self._lock:
            return list(self._blocked)


import time

user_agent_analyzer = UserAgentAnalyzer()
