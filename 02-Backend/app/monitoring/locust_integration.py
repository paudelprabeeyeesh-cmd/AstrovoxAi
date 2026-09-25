"""Locust integration for load testing."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import subprocess
import json
import os


class LoadTestType(Enum):
    LOAD = "load"
    STRESS = "stress"
    SPIKE = "spike"
    ENDURANCE = "endurance"


@dataclass
class LocustConfig:
    test_id: str
    locustfile: str
    host: str = "http://localhost:8000"
    users: int = 10
    spawn_rate: int = 1
    run_time: str = "1m"
    headless: bool = True
    html_report: Optional[str] = None
    csv_prefix: Optional[str] = None


@dataclass
class LocustResult:
    test_id: str
    total_requests: int = 0
    total_failures: int = 0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    rps: float = 0.0
    status: str = "pending"
    raw_output: str = ""


class LocustRunner:
    _results: Dict[str, LocustResult] = {}

    @classmethod
    def run_test(cls, config: LocustConfig) -> LocustResult:
        result = LocustResult(test_id=config.test_id)
        result.status = "running"

        cmd = [
            "locust",
            "-f", config.locustfile,
            "--host", config.host,
            "-u", str(config.users),
            "-r", str(config.spawn_rate),
            "--run-time", config.run_time,
            "--headless",
            "--json"
        ]

        if config.html_report:
            cmd.extend(["--html", config.html_report])
        if config.csv_prefix:
            cmd.extend(["--csv", config.csv_prefix])

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            result.raw_output = proc.stdout + proc.stderr
            result.status = "completed" if proc.returncode == 0 else "failed"
            cls._parse_locust_output(result, proc.stdout)
        except subprocess.TimeoutExpired:
            result.status = "timeout"
        except Exception as e:
            result.status = "error"
            result.raw_output = str(e)

        cls._results[config.test_id] = result
        return result

    @staticmethod
    def _parse_locust_output(result: LocustResult, output: str) -> None:
        lines = output.strip().split('\n')
        for line in lines:
            if 'Request count' in line:
                try:
                    result.total_requests = int(line.split(':')[1].strip())
                except (IndexError, ValueError):
                    pass
            elif 'Failure count' in line:
                try:
                    result.total_failures = int(line.split(':')[1].strip())
                except (IndexError, ValueError):
                    pass
            elif 'Average response time' in line:
                try:
                    result.avg_response_time_ms = float(line.split(':')[1].strip().split()[0])
                except (IndexError, ValueError):
                    pass

    @classmethod
    def get_result(cls, test_id: str) -> Optional[LocustResult]:
        return cls._results.get(test_id)

    @classmethod
    def run_load_test(cls, host: str, users: int = 100, duration: str = "2m") -> LocustResult:
        config = LocustConfig(
            test_id=f"load-{int(datetime.now(timezone.utc).timestamp())}",
            locustfile="tests/performance/locust-load-test.py",
            host=host,
            users=users,
            spawn_rate=10,
            run_time=duration
        )
        return cls.run_test(config)

    @classmethod
    def run_stress_test(cls, host: str, users: int = 1000, duration: str = "5m") -> LocustResult:
        config = LocustConfig(
            test_id=f"stress-{int(datetime.now(timezone.utc).timestamp())}",
            locustfile="tests/performance/locust-load-test.py",
            host=host,
            users=users,
            spawn_rate=50,
            run_time=duration
        )
        return cls.run_test(config)

    @classmethod
    def run_spike_test(cls, host: str, users: int = 500, duration: str = "30s") -> LocustResult:
        config = LocustConfig(
            test_id=f"spike-{int(datetime.now(timezone.utc).timestamp())}",
            locustfile="tests/performance/locust-load-test.py",
            host=host,
            users=users,
            spawn_rate=users,
            run_time=duration
        )
        return cls.run_test(config)
