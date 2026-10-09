import hashlib
import hmac
import json
import math
import os
import random
import re
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ThreatEvent:
    source: str
    event_type: str
    severity: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DetectionRule:
    name: str
    pattern: str
    severity: float = 0.5
    cooldown: float = 60.0
    last_fired: float = 0.0


class AnomalyDetector:
    def __init__(self, threshold: float = 3.0) -> None:
        self._threshold = threshold
        self._baseline: List[float] = []
        self._window: deque = deque(maxlen=1000)

    def observe(self, value: float) -> Optional[Dict[str, Any]]:
        self._window.append(value)
        if len(self._baseline) < 10:
            self._baseline.append(value)
            return None
        mean = sum(self._baseline) / len(self._baseline)
        var = sum((x - mean) ** 2 for x in self._baseline) / len(self._baseline)
        std = math.sqrt(var) + 1e-8
        if abs(value - mean) > self._threshold * std:
            return {"value": value, "mean": mean, "std": std, "z_score": (value - mean) / std}
        self._baseline.append(value)
        return None

    def score(self, value: float) -> float:
        if not self._baseline:
            return 0.0
        mean = sum(self._baseline) / len(self._baseline)
        var = sum((x - mean) ** 2 for x in self._baseline) / len(self._baseline)
        std = math.sqrt(var) + 1e-8
        return abs(value - mean) / std


class BruteForceDetector:
    def __init__(self, window: int = 60, threshold: int = 5) -> None:
        self._window = window
        self._threshold = threshold
        self._attempts: Dict[str, deque] = {}

    def record(self, source: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        dq = self._attempts.setdefault(source, deque())
        dq.append(now)
        while dq and dq[0] < now - self._window:
            dq.popleft()
        if len(dq) >= self._threshold:
            return {"source": source, "attempts": len(dq), "window": self._window}
        return None


class PortScanDetector:
    def __init__(self, window: float = 30.0, unique_threshold: int = 20) -> None:
        self._window = window
        self._unique_threshold = unique_threshold
        self._ports: Dict[str, deque] = {}

    def record(self, source: str, port: int) -> Optional[Dict[str, Any]]:
        now = time.time()
        dq = self._ports.setdefault(source, deque())
        dq.append((now, port))
        while dq and dq[0][0] < now - self._window:
            dq.popleft()
        unique = {p for _, p in dq}
        if len(unique) >= self._unique_threshold:
            return {"source": source, "unique_ports": len(unique), "window": self._window}
        return None


class SignatureDetector:
    def __init__(self) -> None:
        self._signatures: List[Tuple[str, str, float]] = []
        self._last_match: Dict[str, float] = {}

    def add_signature(self, name: str, pattern: str, severity: float = 0.8) -> None:
        self._signatures.append((name, pattern, severity))

    def scan(self, text: str) -> List[Dict[str, Any]]:
        matches = []
        now = time.time()
        for name, pattern, severity in self._signatures:
            last = self._last_match.get(name, 0.0)
            if now - last < 1.0:
                continue
            found = re.search(pattern, text, re.IGNORECASE)
            if found:
                self._last_match[name] = now
                matches.append({"name": name, "severity": severity, "match": found.group(0)})
        return matches


class ThreatDetector:
    def __init__(self) -> None:
        self._anomaly = AnomalyDetector()
        self._brute = BruteForceDetector(threshold=1)
        self._scan = PortScanDetector()
        self._sig = SignatureDetector()
        self._events: List[ThreatEvent] = []

    def add_signature(self, name: str, pattern: str, severity: float = 0.8) -> None:
        self._sig.add_signature(name, pattern, severity)

    def observe_value(self, source: str, value: float) -> Optional[ThreatEvent]:
        anomaly = self._anomaly.observe(value)
        if anomaly:
            event = ThreatEvent(source=source, event_type="anomaly", severity=min(1.0, anomaly["z_score"] / 6.0), evidence=anomaly)
            self._events.append(event)
            return event
        return None

    def record_auth(self, source: str) -> Optional[ThreatEvent]:
        hit = self._brute.record(source)
        if hit:
            event = ThreatEvent(source=source, event_type="brute_force", severity=0.9, evidence=hit)
            self._events.append(event)
            return event
        return None

    def record_connection(self, source: str, port: int) -> Optional[ThreatEvent]:
        hit = self._scan.record(source, port)
        if hit:
            event = ThreatEvent(source=source, event_type="port_scan", severity=0.8, evidence=hit)
            self._events.append(event)
            return event
        return None

    def inspect(self, text: str) -> List[Dict[str, Any]]:
        return self._sig.scan(text)

    def recent_events(self, limit: int = 100) -> List[ThreatEvent]:
        return self._events[-limit:]
