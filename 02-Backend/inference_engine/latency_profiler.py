
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from time import time
from enum import Enum
import numpy as np


class LatencyEventType(Enum):
    STEP = "step"
    PREFILL = "prefill"
    DECODE = "decode"
    FULL = "full"
    REQUEST = "request"


@dataclass
class LatencyEvent:
    event_type: LatencyEventType
    latency_ms: float
    tokens: int = 0
    timestamp: float = field(default_factory=time)
    metadata: Dict = field(default_factory=dict)

    @property
    def tokens_per_second(self) -> float:
        if self.tokens <= 0 or self.latency_ms <= 0:
            return 0.0
        return self.tokens / (self.latency_ms / 1000.0)

    @property
    def ms_per_token(self) -> float:
        if self.tokens <= 0:
            return 0.0
        return self.latency_ms / self.tokens


@dataclass
class ProfilingContext:
    name: str
    start_time: float = field(default_factory=time)
    end_time: Optional[float] = None
    tokens: int = 0
    metadata: Dict = field(default_factory=dict)

    @property
    def elapsed_ms(self) -> float:
        end = self.end_time if self.end_time is not None else time()
        return (end - self.start_time) * 1000.0

    @property
    def elapsed_seconds(self) -> float:
        return self.elapsed_ms / 1000.0


@dataclass
class LatencyProfiler:
    warmup_steps: int = 0
    device: str = "cpu"
    events: List[LatencyEvent] = field(default_factory=list)
    _contexts: Dict[str, ProfilingContext] = field(default_factory=dict)

    def __post_init__(self):
        self._events_cache: List[LatencyEvent] = []

    def start_event(
        self,
        name: str,
        event_type: LatencyEventType = LatencyEventType.STEP,
        metadata: Optional[Dict] = None,
    ) -> ProfilingContext:
        ctx = ProfilingContext(name=name, metadata=metadata or {})
        ctx._event_type = event_type
        self._contexts[name] = ctx
        return ctx

    def stop_event(
        self,
        ctx: ProfilingContext,
        tokens: int = 0,
        metadata: Optional[Dict] = None,
    ) -> LatencyEvent:
        ctx.end_time = time()
        ctx.tokens = tokens
        event = LatencyEvent(
            event_type=ctx._event_type,
            latency_ms=ctx.elapsed_ms,
            tokens=tokens,
            metadata={**(ctx.metadata or {}), **(metadata or {})},
        )
        self.events.append(event)
        self._events_cache.append(event)
        return event

    def record_latency(
        self,
        event_type: LatencyEventType,
        latency_ms: float,
        tokens: int = 0,
        metadata: Optional[Dict] = None,
    ) -> LatencyEvent:
        event = LatencyEvent(
            event_type=event_type,
            latency_ms=latency_ms,
            tokens=tokens,
            metadata=metadata or {},
        )
        self.events.append(event)
        self._events_cache.append(event)
        return event

    def step_latency(
        self,
        latency_ms: float,
        tokens: int = 0,
    ) -> LatencyEvent:
        return self.record_latency(
            LatencyEventType.STEP, latency_ms, tokens=tokens
        )

    def get_events(self) -> List[LatencyEvent]:
        return list(self.events)

    def get_events_by_type(
        self, event_type: LatencyEventType
    ) -> List[LatencyEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_name(
        self, name: str
    ) -> List[LatencyEvent]:
        return [e for e in self.events if any(
            n in e.metadata.get("name", "") for n in [name]
        )]

    def summary(self) -> Dict:
        if not self.events:
            return {
                "total_events": 0,
                "total_steps": 0,
                "total_prefill": 0,
                "total_decode": 0,
                "total_tokens": 0,
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p90_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "total_tokens_per_second": 0.0,
                "avg_tokens_per_second": 0.0,
                "ttft_ms": 0.0,
            }
        latencies = [e.latency_ms for e in self.events]
        total_tokens = sum(e.tokens for e in self.events)
        total_ms = sum(latencies)
        events_with_tokens = [e for e in self.events if e.tokens > 0]
        if total_ms > 0:
            tps = total_tokens / (total_ms / 1000.0)
        else:
            tps = 0.0
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        p50 = sorted_latencies[int(n * 0.5)] if n > 0 else 0.0
        p90 = sorted_latencies[int(n * 0.9)] if n > 0 else 0.0
        p99 = sorted_latencies[int(n * 0.99)] if n > 0 else 0.0
        ttft = next(
            (e.latency_ms for e in self.events if e.event_type == LatencyEventType.PREFILL),
            0.0,
        )
        return {
            "total_events": len(self.events),
            "total_steps": len(self.get_events_by_type(LatencyEventType.STEP)),
            "total_prefill": len(self.get_events_by_type(LatencyEventType.PREFILL)),
            "total_decode": len(self.get_events_by_type(LatencyEventType.DECODE)),
            "total_tokens": total_tokens,
            "avg_latency_ms": float(np.mean(latencies)),
            "min_latency_ms": float(np.min(latencies)),
            "max_latency_ms": float(np.max(latencies)),
            "p50_latency_ms": p50,
            "p90_latency_ms": p90,
            "p99_latency_ms": p99,
            "total_tokens_per_second": tps,
            "avg_tokens_per_second": tps / max(len(events_with_tokens), 1),
            "ttft_ms": ttft,
        }

    def reset(self) -> None:
        self.events = []
        self._events_cache = []
        self._contexts = {}

    def get_tokens_per_second(self) -> float:
        if not self.events:
            return 0.0
        total_ms = sum(e.latency_ms for e in self.events)
        if total_ms <= 0:
            return 0.0
        total_tokens = sum(e.tokens for e in self.events)
        return total_tokens / (total_ms / 1000.0)

    def get_avg_latency(self) -> float:
        if not self.events:
            return 0.0
        return float(np.mean([e.latency_ms for e in self.events]))

    def get_min_latency(self) -> float:
        if not self.events:
            return 0.0
        return float(np.min([e.latency_ms for e in self.events]))

    def get_max_latency(self) -> float:
        if not self.events:
            return 0.0
        return float(np.max([e.latency_ms for e in self.events]))
