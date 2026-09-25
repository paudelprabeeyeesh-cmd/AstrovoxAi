from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class APIAbuseDetector:
    def __init__(self, rate_limit: int = 100, window_seconds: int = 60, block_threshold: int = 5):
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        self.block_threshold = block_threshold
        self.request_log: Dict[str, List[datetime]] = defaultdict(list)
        self.blocked_ips: Dict[str, datetime] = {}
        self.stats = {'total_requests': 0, 'blocked_requests': 0, 'suspicious_requests': 0}

    def record_request(self, ip: str, endpoint: str, payload_size: int = 0) -> Tuple[bool, Optional[str]]:
        self.stats['total_requests'] += 1
        if ip in self.blocked_ips:
            if datetime.now() - self.blocked_ips[ip] < timedelta(minutes=10):
                self.stats['blocked_requests'] += 1
                return False, 'IP temporarily blocked'
            del self.blocked_ips[ip]
        now = datetime.now()
        self.request_log[ip] = [t for t in self.request_log[ip] if now - t < timedelta(seconds=self.window_seconds)]
        self.request_log[ip].append(now)
        if len(self.request_log[ip]) > self.rate_limit:
            self.stats['suspicious_requests'] += 1
            self.blocked_ips[ip] = now
            return False, 'Rate limit exceeded'
        if payload_size > 10 * 1024 * 1024:
            self.stats['suspicious_requests'] += 1
            return False, 'Payload too large'
        return True, None

    def is_blocked(self, ip: str) -> bool:
        if ip in self.blocked_ips:
            if datetime.now() - self.blocked_ips[ip] < timedelta(minutes=10):
                return True
            del self.blocked_ips[ip]
        return False

    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()
