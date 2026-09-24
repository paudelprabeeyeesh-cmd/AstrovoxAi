import time
import threading
import traceback
import logging
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field


@dataclass
class ErrorRecord:
    error_id: str
    error_type: str
    message: str
    status_code: int
    path: str
    method: str
    timestamp: float
    traceback_str: str
    tags: Set[str] = field(default_factory=set)
    retry_count: int = 0
    handled: bool = False


@dataclass
class ErrorHandlerConfig:
    error_retry_delays: Dict[int, float] = field(default_factory=lambda: {
        408: 1.0,
        429: 2.0,
        500: 1.0,
        502: 2.0,
        503: 3.0,
        504: 2.0,
    })
    max_retries: int = 3
    log_tracebacks: bool = True
    error_tags: Set[str] = field(default_factory=set)


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 500, retryable: bool = False):
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(message)


class BadRequestError(APIError):
    def __init__(self, message: str = "Bad Request"):
        super().__init__(message, status_code=400, retryable=False)


class RateLimitError(APIError):
    def __init__(self, message: str = "Rate Limit Exceeded"):
        super().__init__(message, status_code=429, retryable=True)


class UpstreamError(APIError):
    def __init__(self, message: str = "Upstream Error", status_code: int = 502):
        super().__init__(message, status_code=status_code, retryable=True)


class ServerError(APIError):
    def __init__(self, message: str = "Internal Server Error"):
        super().__init__(message, status_code=500, retryable=False)


class ErrorHandler:
    def __init__(self, config: Optional[ErrorHandlerConfig] = None):
        self._config = config or ErrorHandlerConfig()
        self._errors: Dict[str, ErrorRecord] = {}
        self._lock = threading.Lock()
        self._error_counts: Dict[str, int] = {}
        self._status_counts: Dict[int, int] = {}
        self._handler: Optional[Callable] = None

    def register_handler(self, handler: Callable[[ErrorRecord], None]):
        self._handler = handler

    def handle(
        self,
        exc: Exception,
        path: str = "",
        method: str = "",
        tags: Optional[Set[str]] = None,
    ) -> ErrorRecord:
        error_id = self._generate_id()
        if isinstance(exc, APIError):
            error_type = exc.__class__.__name__
            status_code = exc.status_code
        elif isinstance(exc, ValueError):
            error_type = "ValueError"
            status_code = 400
        else:
            error_type = type(exc).__name__
            status_code = 500

        tb_str = traceback.format_exc() if self._config.log_tracebacks else ""
        record = ErrorRecord(
            error_id=error_id,
            error_type=error_type,
            message=str(exc),
            status_code=status_code,
            path=path,
            method=method,
            timestamp=time.time(),
            traceback_str=tb_str,
            tags=tags or self._config.error_tags,
        )
        with self._lock:
            self._errors[error_id] = record
            self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
            self._status_counts[status_code] = self._status_counts.get(status_code, 0) + 1
        if self._handler:
            try:
                self._handler(record)
            except Exception:
                pass
        return record

    def retry_with_backoff(
        self,
        func: Callable,
        path: str = "",
        method: str = "",
        tags: Optional[Set[str]] = None,
        max_retries: Optional[int] = None,
    ):
        max_r = max_retries or self._config.max_retries
        last_error = None
        for attempt in range(max_r):
            try:
                return func()
            except Exception as exc:
                last_error = exc
                if self._config.log_tracebacks:
                    self.handle(exc, path=path, method=method, tags=tags)
                if attempt < max_r - 1:
                    if isinstance(exc, APIError):
                        delay = self._config.error_retry_delays.get(exc.status_code, 1.0)
                    else:
                        delay = 1.0
                    self._sleep(delay)
        if last_error:
            raise last_error

    def _sleep(self, delay: float):
        start = time.time()
        while time.time() - start < delay:
            pass

    def get_error(self, error_id: str) -> Optional[ErrorRecord]:
        with self._lock:
            return self._errors.get(error_id)

    def get_errors(
        self,
        error_type: Optional[str] = None,
        status_code: Optional[int] = None,
        path: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ErrorRecord]:
        with self._lock:
            results = list(self._errors.values())
        if error_type is not None:
            results = [e for e in results if e.error_type == error_type]
        if status_code is not None:
            results = [e for e in results if e.status_code == status_code]
        if path is not None:
            results = [e for e in results if e.path == path]
        results.sort(key=lambda e: e.timestamp, reverse=True)
        if limit is not None:
            results = results[:limit]
        return results

    @property
    def error_summary(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._error_counts)

    @property
    def status_summary(self) -> Dict[int, int]:
        with self._lock:
            return dict(self._status_counts)

    @property
    def total_errors(self) -> int:
        with self._lock:
            return len(self._errors)

    def clear(self):
        with self._lock:
            self._errors.clear()
            self._error_counts.clear()
            self._status_counts.clear()

    def _generate_id(self) -> str:
        return f"err_{int(time.time() * 1000)}_{id(self) & 0xFFFF:04x}"


def format_error_response(error_record: ErrorRecord) -> Dict[str, any]:
    return {
        "error_id": error_record.error_id,
        "error_type": error_record.error_type,
        "message": error_record.message,
        "status_code": error_record.status_code,
        "path": error_record.path,
        "timestamp": error_record.timestamp,
    }


def get_http_status_text(status_code: int) -> str:
    texts = {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        408: "Request Timeout",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }
    return texts.get(status_code, "Unknown")
