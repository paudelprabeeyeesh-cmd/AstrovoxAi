"""Monitoring module."""


class _ErrorTracker:
    def get_error_summary(self):
        return {"total": 0, "by_severity": {}}

    def get_errors(self, severity=None, limit=100):
        return []


class _PerformanceMonitor:
    def get_system_stats(self):
        return {"cpu": 0, "memory": 0, "disk": 0}

    def get_all_request_stats(self):
        return {"total": 0, "errors": 0}


class _UptimeTracker:
    def get_uptime(self):
        return {"uptime_seconds": 0, "status": "healthy"}


error_tracker = _ErrorTracker()
performance_monitor = _PerformanceMonitor()
uptime_tracker = _UptimeTracker()
