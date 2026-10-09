import time
import threading
import uuid
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    request_id: str
    method: str
    path: str
    status_code: int
    client_ip: str
    user_agent: str
    timestamp: float
    response_time_ms: float
    bytes_sent: int
    error: Optional[str] = None
    tags: Set[str] = field(default_factory=set)


@dataclass
class RequestMetrics:
    total_requests: int = 0
    error_requests: int = 0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    unique_ips: int = 0
    requests_per_minute: float = 0.0


class RequestLogger:
    def __init__(
        self,
        max_entries: int = 10_000,
        retention_seconds: float = 3600.0,
        p95_window: int = 1000,
    ):
        self._max_entries = max_entries
        self._retention = retention_seconds
        self._p95_window = p95_window
        self._entries: Dict[str, LogEntry] = {}
        self._lock = threading.Lock()
        self._response_times: List[float] = []
        self._ip_counts: Dict[str, int] = {}
        self._path_counts: Dict[str, int] = {}
        self._status_counts: Dict[int, int] = {}
        self._error_messages: Dict[str, int] = {}
        self._minute_buckets: Dict[int, int] = {}
        self._total_bytes = 0

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        client_ip: str,
        user_agent: str,
        response_time_ms: float,
        bytes_sent: int = 0,
        error: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> str:
        request_id = str(uuid.uuid4())
        entry = LogEntry(
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            client_ip=client_ip,
            user_agent=user_agent,
            timestamp=time.time(),
            response_time_ms=response_time_ms,
            bytes_sent=bytes_sent,
            error=error,
            tags=tags or set(),
        )
        with self._lock:
            self._entries[request_id] = entry
            self._response_times.append(response_time_ms)
            self._ip_counts[client_ip] = self._ip_counts.get(client_ip, 0) + 1
            self._path_counts[path] = self._path_counts.get(path, 0) + 1
            self._status_counts[status_code] = self._status_counts.get(status_code, 0) + 1
            self._total_bytes += bytes_sent
            if status_code >= 400:
                self._error_messages[error or "unknown_error"] = (
                    self._error_messages.get(error or "unknown_error", 0) + 1
                )
            minute_bucket = int(time.time() // 60)
            self._minute_buckets[minute_bucket] = self._minute_buckets.get(minute_bucket, 0) + 1
            self._purge_expired()
        return request_id

    def _purge_expired(self):
        if len(self._entries) <= self._max_entries:
            return
        cutoff = time.time() - self._retention
        expired = [k for k, v in self._entries.items() if v.timestamp < cutoff]
        for k in expired:
            del self._entries[k]

    def get_entry(self, request_id: str) -> Optional[LogEntry]:
        with self._lock:
            return self._entries.get(request_id)

    def get_entries(
        self,
        method: Optional[str] = None,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        path: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[LogEntry]:
        with self._lock:
            results = list(self._entries.values())
        if method is not None:
            results = [e for e in results if e.method == method]
        if status_min is not None:
            results = [e for e in results if e.status_code >= status_min]
        if status_max is not None:
            results = [e for e in results if e.status_code <= status_max]
        if path is not None:
            results = [e for e in results if e.path == path]
        results.sort(key=lambda e: e.timestamp, reverse=True)
        if limit is not None:
            results = results[:limit]
        return results

    def get_metrics(self) -> RequestMetrics:
        with self._lock:
            if not self._entries:
                return RequestMetrics()
            total = len(self._entries)
            errors = sum(1 for e in self._entries.values() if e.status_code >= 400)
            rt_values = sorted(e.response_time_ms for e in self._entries.values())
            p95_idx = int(len(rt_values) * 0.95)
            rpm = self._requests_per_minute()
            return RequestMetrics(
                total_requests=total,
                error_requests=errors,
                avg_response_time_ms=sum(rt_values) / len(rt_values),
                p95_response_time_ms=rt_values[min(p95_idx, len(rt_values) - 1)],
                max_response_time_ms=max(rt_values),
                unique_ips=len(self._ip_counts),
                requests_per_minute=round(rpm, 2),
            )

    def _requests_per_minute(self) -> float:
        now = int(time.time() // 60)
        total = 0
        for m in range(now - 1, now + 1):
            total += self._minute_buckets.get(m, 0)
        return float(total) / 2.0

    @property
    def error_summary(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._error_messages)

    @property
    def top_paths(self) -> Dict[str, int]:
        with self._lock:
            return dict(sorted(self._path_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    @property
    def total_bytes_logged(self) -> int:
        with self._lock:
            return self._total_bytes

    def clear(self):
        with self._lock:
            self._entries.clear()
            self._response_times.clear()
            self._ip_counts.clear()
            self._path_counts.clear()
            self._status_counts.clear()
            self._error_messages.clear()
            self._minute_buckets.clear()
            self._total_bytes = 0


class RequestLoggerProxy:
    def __init__(self, logger: RequestLogger):
        self._logger = logger

    def log(self, method: str, path: str, status_code: int, client_ip: str,
            user_agent: str, response_time_ms: float, bytes_sent: int = 0) -> str:
        return self._logger.log_request(
            method=method,
            path=path,
            status_code=status_code,
            client_ip=client_ip,
            user_agent=user_agent,
            response_time_ms=response_time_ms,
            bytes_sent=bytes_sent,
        )

    def metrics(self) -> RequestMetrics:
        return self._logger.get_metrics()
