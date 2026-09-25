"""Performance profiling with flame graphs."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import time
import cProfile
import pstats
import io
import tracemalloc


class ProfileStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"


@dataclass
class ProfileSample:
    timestamp: datetime
    function_name: str
    cumulative_time: float
    self_time: float
    call_count: int
    memory_usage_bytes: int


@dataclass
class FlameGraphData:
    profile_id: str
    samples: List[ProfileSample]
    total_samples: int
    max_memory_bytes: int
    total_time_seconds: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PerformanceProfiler:
    _profiles: Dict[str, FlameGraphData] = {}
    _active_profiles: Dict[str, cProfile.Profile] = {}
    _status: Dict[str, ProfileStatus] = {}

    @classmethod
    def start_profile(cls, profile_id: str) -> None:
        if profile_id in cls._active_profiles:
            return
        profiler = cProfile.Profile()
        profiler.enable()
        cls._active_profiles[profile_id] = profiler
        cls._status[profile_id] = ProfileStatus.RUNNING
        tracemalloc.start()

    @classmethod
    def stop_profile(cls, profile_id: str) -> Optional[FlameGraphData]:
        profiler = cls._active_profiles.get(profile_id)
        if not profiler:
            return None
        profiler.disable()
        tracemalloc.stop()

        stream = io.StringIO()
        ps = pstats.Stats(profiler, stream=stream)
        ps.sort_stats('cumulative')
        ps.print_stats()

        stats_output = stream.getvalue()
        samples = cls._parse_profile_stats(stats_output)

        current, peak = tracemalloc.get_traced_memory()
        flame_data = FlameGraphData(
            profile_id=profile_id,
            samples=samples,
            total_samples=len(samples),
            max_memory_bytes=peak,
            total_time_seconds=sum(s.cumulative_time for s in samples)
        )

        cls._profiles[profile_id] = flame_data
        cls._status[profile_id] = ProfileStatus.COMPLETED
        del cls._active_profiles[profile_id]
        return flame_data

    @staticmethod
    def _parse_profile_stats(stats_output: str) -> List[ProfileSample]:
        samples = []
        lines = stats_output.split('\n')
        for line in lines[6:]:
            parts = line.strip().split()
            if len(parts) >= 4:
                try:
                    call_count = int(parts[0])
                    self_time = float(parts[1])
                    cum_time = float(parts[3])
                    function_name = ' '.join(parts[5:]) if len(parts) > 5 else parts[4]
                    samples.append(ProfileSample(
                        timestamp=datetime.now(timezone.utc),
                        function_name=function_name,
                        cumulative_time=cum_time,
                        self_time=self_time,
                        call_count=call_count,
                        memory_usage_bytes=0
                    ))
                except (ValueError, IndexError):
                    continue
        return samples[:50]

    @classmethod
    def get_profile(cls, profile_id: str) -> Optional[FlameGraphData]:
        return cls._profiles.get(profile_id)

    @classmethod
    def get_flame_graph_data(cls, profile_id: str) -> List[Dict[str, Any]]:
        profile = cls._profiles.get(profile_id)
        if not profile:
            return []

        return [
            {
                "name": sample.function_name,
                "value": sample.cumulative_time,
                "self_time": sample.self_time,
                "call_count": sample.call_count
            }
            for sample in profile.samples
        ]

    @classmethod
    def get_profile_summary(cls, profile_id: str) -> Dict[str, Any]:
        profile = cls._profiles.get(profile_id)
        if not profile:
            return {}
        return {
            "profile_id": profile_id,
            "total_time_seconds": profile.total_time_seconds,
            "max_memory_bytes": profile.max_memory_bytes,
            "total_samples": profile.total_samples,
            "top_functions": [
                {"name": s.function_name, "time": s.cumulative_time}
                for s in profile.samples[:10]
            ]
        }

    @classmethod
    def clear_profiles(cls) -> None:
        cls._profiles.clear()
        cls._active_profiles.clear()
        cls._status.clear()
