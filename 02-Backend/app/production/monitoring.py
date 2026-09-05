"""Long-running stability monitoring for production deployment.

Provides:
- Memory leak detection
- Performance monitoring
- Health checks over time
- Automatic alerting
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional


@dataclass
class StabilityMetrics:
    """Metrics for long-running stability."""
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    active_connections: int = 0
    request_rate: float = 0.0
    error_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


class StabilityMonitor:
    """Monitors system stability over time."""
    
    def __init__(self, history_size: int = 1000) -> None:
        self.history: Deque[StabilityMetrics] = deque(maxlen=history_size)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._alert_callbacks: List[Callable[[StabilityMetrics], None]] = []
    
    def add_alert_callback(self, callback: Callable[[StabilityMetrics], None]) -> None:
        """Add a callback for alerts."""
        self._alert_callbacks.append(callback)
    
    async def _collect_metrics(self) -> StabilityMetrics:
        """Collect current system metrics."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return StabilityMetrics(
            memory_usage_mb=memory_info.rss / 1024 / 1024,
            cpu_usage_percent=process.cpu_percent(),
            timestamp=time.time()
        )
    
    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                metrics = await self._collect_metrics()
                self.history.append(metrics)
                
                # Check for memory leaks (if memory grows consistently)
                if len(self.history) >= 10:
                    recent = [m.memory_usage_mb for m in list(self.history)[-10:]]
                    if all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
                        avg_growth = (recent[-1] - recent[0]) / len(recent)
                        if avg_growth > 10:  # More than 10MB growth per sample
                            await self._trigger_alert(metrics)
                
                await asyncio.sleep(10)  # Collect every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue monitoring
                print(f"Monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _trigger_alert(self, metrics: StabilityMetrics) -> None:
        """Trigger alerts for stability issues."""
        for callback in self._alert_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                print(f"Alert callback error: {e}")
    
    async def start(self) -> None:
        """Start monitoring."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
    
    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    def get_current_metrics(self) -> Optional[StabilityMetrics]:
        """Get the most recent metrics."""
        if self.history:
            return self.history[-1]
        return None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of stability metrics."""
        if not self.history:
            return {"samples": 0}
        
        memory_values = [m.memory_usage_mb for m in self.history]
        cpu_values = [m.cpu_usage_percent for m in self.history]
        
        return {
            "samples": len(self.history),
            "memory_mb": {
                "min": min(memory_values),
                "max": max(memory_values),
                "avg": sum(memory_values) / len(memory_values),
                "latest": memory_values[-1]
            },
            "cpu_percent": {
                "min": min(cpu_values),
                "max": max(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values),
                "latest": cpu_values[-1]
            }
        }


# Global stability monitor
_stability_monitor: Optional[StabilityMonitor] = None


def get_stability_monitor() -> StabilityMonitor:
    """Get global stability monitor."""
    global _stability_monitor
    if _stability_monitor is None:
        _stability_monitor = StabilityMonitor()
    return _stability_monitor