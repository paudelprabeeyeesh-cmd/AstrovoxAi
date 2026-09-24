import time
import threading
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TrafficRecord:
    ip: str
    timestamp: float
    path: str
    method: str
    user_agent: str
    payload_size: int
    is_suspicious: bool = False


@dataclass
class ScrubResult:
    is_allowed: bool
    reason: str
    risk_score: float


class TrafficScrubber:
    def __init__(
        self,
        suspicious_user_agents: Optional[Set[str]] = None,
        max_payload_size: int = 10_000_000,
        known_bad_ips: Optional[Set[str]] = None,
    ):
        self._suspicious_agents = suspicious_user_agents or {
            "scanner", "sqlmap", "nmap", "nikto", "dirbuster",
        }
        self._max_payload_size = max_payload_size
        self._known_bad_ips = known_bad_ips or set()
        self._ip_hits: Dict[str, List[float]] = {}

    def _is_suspicious_ua(self, user_agent: str) -> bool:
        ua_lower = user_agent.lower()
        return any(s in ua_lower for s in self._suspicious_agents)

    def scrub(self, record: TrafficRecord) -> ScrubResult:
        risk_score = 0.0
        reasons = []

        if record.ip in self._known_bad_ips:
            risk_score += 1.0
            reasons.append("known_bad_ip")

        if record.payload_size > self._max_payload_size:
            risk_score += 0.5
            reasons.append("payload_too_large")

        if self._is_suspicious_ua(record.user_agent):
            risk_score += 0.8
            reasons.append("suspicious_user_agent")

        now = time.time()
        with threading.Lock():
            hits = self._ip_hits.setdefault(record.ip, [])
            hits.append(now)
            cutoff = now - 60.0
            self._ip_hits[record.ip] = [t for t in hits if t >= cutoff]

        hit_count = len(self._ip_hits[record.ip])
        if hit_count > 100:
            risk_score += 0.9
            reasons.append(f"high_frequency_{hit_count}_reqs_per_min")

        is_allowed = risk_score < 0.7
        reason = ";".join(reasons) if reasons else "clean"
        return ScrubResult(
            is_allowed=is_allowed,
            reason=reason,
            risk_score=risk_score,
        )


class BadTrafficClassifier:
    def __init__(self):
        self._request_patterns: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._thresholds = {
            "requests_per_second": 50.0,
            "error_rate": 0.9,
            "avg_payload_anomaly": 100_000.0,
        }

    def record_request(self, ip: str, is_error: bool, payload_size: int):
        now = time.time()
        with self._lock:
            self._request_patterns[ip].append(
                (now, is_error, payload_size)
            )
            cutoff = now - 60.0
            self._request_patterns[ip] = [
                (t, e, p) for t, e, p in self._request_patterns[ip]
                if t >= cutoff
            ]

    def classify(self, ip: str) -> Dict[str, any]:
        with self._lock:
            entries = self._request_patterns.get(ip, [])
        if not entries:
            return {"classification": "unknown", "confidence": 0.0, "features": {}}

        now = time.time()
        recent = [(t, e, p) for t, e, p in entries if now - t <= 10.0]
        total_errors = sum(1 for _, e, _ in entries if e)
        error_rate = total_errors / len(entries) if entries else 0.0
        rps = len(recent) / 10.0 if recent else 0.0
        avg_payload = (
            sum(p for _, _, p in entries) / len(entries) if entries else 0.0
        )

        is_bad = (
            rps > self._thresholds["requests_per_second"]
            or error_rate > self._thresholds["error_rate"]
            or avg_payload > self._thresholds["avg_payload_anomaly"]
        )

        confidence = min(1.0, (
            max(rps / self._thresholds["requests_per_second"], 0.0) * 0.4
            + error_rate * 0.4
            + min(avg_payload / self._thresholds["avg_payload_anomaly"], 1.0) * 0.2
        ))

        return {
            "classification": "bad" if is_bad else "good",
            "confidence": round(confidence, 4),
            "features": {
                "requests_per_second": round(rps, 2),
                "error_rate": round(error_rate, 4),
                "avg_payload_size": round(avg_payload, 2),
            },
        }


class DDoSMitigator:
    def __init__(
        self,
        cdn_enabled: bool = True,
        scrubber: Optional[TrafficScrubber] = None,
        classifier: Optional[BadTrafficClassifier] = None,
    ):
        self._cdn_enabled = cdn_enabled
        self._scrubber = scrubber or TrafficScrubber()
        self._classifier = classifier or BadTrafficClassifier()
        self._blocked_ips: Set[str] = set()
        self._lock = threading.Lock()
        self._total_requests = 0
        self._blocked_requests = 0

    def inspect(self, record: TrafficRecord) -> ScrubResult:
        with self._lock:
            self._total_requests += 1

        scrub_result = self._scrubber.scrub(record)
        classification = self._classifier.classify(record.ip)

        is_bad_traffic = (
            not scrub_result.is_allowed
            or classification["classification"] == "bad"
        )

        if is_bad_traffic:
            with self._lock:
                self._blocked_requests += 1
                self._blocked_ips.add(record.ip)

        if is_bad_traffic:
            return ScrubResult(
                is_allowed=False,
                reason=f"blocked:{scrub_result.reason}|{classification['classification']}",
                risk_score=max(scrub_result.risk_score, classification["confidence"]),
            )

        self._classifier.record_request(
            record.ip, is_error=False, payload_size=record.payload_size
        )
        return ScrubResult(is_allowed=True, reason="clean", risk_score=0.0)

    @property
    def blocked_ips(self) -> Set[str]:
        with self._lock:
            return set(self._blocked_ips)

    @property
    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "total_requests": self._total_requests,
                "blocked_requests": self._blocked_requests,
                "unique_blocked_ips": len(self._blocked_ips),
            }
