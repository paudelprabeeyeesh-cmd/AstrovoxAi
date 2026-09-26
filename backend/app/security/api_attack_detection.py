"""API attack detection with OWASP-style pattern matching and anomaly scoring."""
import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class AttackSeverity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AttackFinding:
    finding_id: str
    attack_type: str
    severity: AttackSeverity
    description: str
    timestamp: float
    source_ip: str
    endpoint: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    is_resolved: bool = False


class APIAttackDetector:
    def __init__(self):
        self._findings: List[AttackFinding] = []
        self._lock = __import__("threading").Lock()
        self._signatures = self._build_signatures()
        self._rate_limit_violations: Dict[str, List[float]] = {}
        self._blocked_ips: Dict[str, float] = {}
        self._rapid_threshold = 100
        self._rapid_window = 60.0

    def _build_signatures(self) -> List[tuple]:
        return [
            (re.compile(r"(?i)\b(union\s+all\s+select|select\s+.*\s+from|insert\s+into|update\s+.*\s+set|delete\s+from)\b"), "sql_injection", AttackSeverity.CRITICAL, "SQL injection pattern detected"),
            (re.compile(r"(?i)(<script[^>]*>.*?</script>|javascript:|onerror\s*=|onload\s*=)"), "xss", AttackSeverity.HIGH, "Cross-site scripting pattern detected"),
            (re.compile(r"(?i)(\.\.\/|\.\.\\\\|%2e%2e%2f|%2e%2e%5c)"), "path_traversal", AttackSeverity.HIGH, "Path traversal pattern detected"),
            (re.compile(r"(?i)(exec\s*\(|eval\s*\(|system\s*\(|passthru\s*\(|shell_exec\s*\(|popen\s*\(|proc_open\s*\()"), "command_injection", AttackSeverity.CRITICAL, "Command injection pattern detected"),
            (re.compile(r"(?i)(<\|?[^>]*\|?>|{\{|%00|%0d%0a)"), "template_injection", AttackSeverity.HIGH, "Template or expression injection detected"),
            (re.compile(r"(?i)(content-type:\s*application\/x-www-form-urlencoded.*?select|content-length:\s*[0-9]{5,})"), "http_parameter_pollution", AttackSeverity.MEDIUM, "HTTP parameter pollution or oversized request detected"),
            (re.compile(r"(?i)(<xml>|<![CDATA[|ENTITY\s+xml)"), "xxe", AttackSeverity.HIGH, "XML external entity injection detected"),
            (re.compile(r"(?i)(grpc|graphql|proto).*(/|\\\\|%2f).*(etc/passwd|etc/shadow|proc/self)"), "ssrf", AttackSeverity.CRITICAL, "Server-side request forgery detected"),
            (re.compile(r"(?i)(authorization:\s*bearer\s+[^\s]+|api[_-]?key\s*[:=]\s*[^\s]+)\s+in\s+(body|query)"), "credential_leak", AttackSeverity.HIGH, "Credential leak in request body or query"),
            (re.compile(r"(?i)(base64,|data:text/html).*(alert\(|onerror|onload)"), "data_uri_xss", AttackSeverity.MEDIUM, "Data URI XSS payload detected"),
        ]

    def inspect_request(self, source_ip: str, endpoint: str, method: str, headers: Dict[str, str], query_params: Dict[str, str], body: Optional[str] = None) -> List[AttackFinding]:
        findings = []
        now = time.time()

        if self._is_blocked_ip(source_ip):
            finding = AttackFinding(
                finding_id=hashlib.sha256(f"{source_ip}:{endpoint}:{now}:blocked".encode()).hexdigest()[:16],
                attack_type="blocked_ip",
                severity=AttackSeverity.HIGH,
                description="Request from blocked IP address",
                timestamp=now,
                source_ip=source_ip,
                endpoint=endpoint,
                evidence={"ip": source_ip},
            )
            findings.append(finding)
            return findings

        self._check_rate_limit(source_ip, endpoint)
        haystack = " ".join([
            method.lower(),
            endpoint.lower(),
            " ".join(f"{k}={v}" for k, v in headers.items()),
            " ".join(f"{k}={v}" for k, v in query_params.items()),
            body or "",
        ])

        for pattern, attack_type, severity, description in self._signatures:
            matches = pattern.findall(haystack)
            if matches:
                finding = AttackFinding(
                    finding_id=hashlib.sha256(f"{source_ip}:{endpoint}:{attack_type}:{now}".encode()).hexdigest()[:16],
                    attack_type=attack_type,
                    severity=severity,
                    description=description,
                    timestamp=now,
                    source_ip=source_ip,
                    endpoint=endpoint,
                    evidence={"matches": len(matches), "sample": matches[0] if matches else ""},
                )
                findings.append(finding)

        if findings:
            with self._lock:
                self._findings.extend(findings)
                if len(self._findings) > 10000:
                    self._findings = self._findings[-5000:]
            for finding in findings:
                logger.warning("API attack detected: %s from %s on %s", finding.attack_type, source_ip, endpoint)

        return findings

    def block_ip(self, ip: str, ttl: int = 3600):
        with self._lock:
            self._blocked_ips[ip] = time.time() + ttl
        logger.warning("Blocked IP %s for %s seconds", ip, ttl)

    def unblock_ip(self, ip: str):
        with self._lock:
            self._blocked_ips.pop(ip, None)

    def get_findings(self, min_severity: AttackSeverity = AttackSeverity.MEDIUM, limit: int = 100) -> List[Dict[str, Any]]:
        cutoff = min(s.value for s in AttackSeverity if s.value in (AttackSeverity.LOW.value, AttackSeverity.MEDIUM.value, AttackSeverity.HIGH.value, AttackSeverity.CRITICAL.value))
        with self._lock:
            return [
                {
                    "finding_id": f.finding_id,
                    "attack_type": f.attack_type,
                    "severity": f.severity.value,
                    "description": f.description,
                    "source_ip": f.source_ip,
                    "endpoint": f.endpoint,
                    "timestamp": f.timestamp,
                    "is_resolved": f.is_resolved,
                }
                for f in self._findings
                if not f.is_resolved and f.severity.value >= min_severity.value
            ][-limit:]

    def get_attack_summary(self) -> Dict[str, Any]:
        with self._lock:
            by_type: Dict[str, int] = {}
            by_severity: Dict[str, int] = {}
            for f in self._findings:
                by_type[f.attack_type] = by_type.get(f.attack_type, 0) + 1
                by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1
            return {
                "total_findings": len(self._findings),
                "by_attack_type": by_type,
                "by_severity": by_severity,
                "blocked_ips": len(self._blocked_ips),
                "generated_at": time.time(),
            }

    def _is_blocked_ip(self, ip: str) -> bool:
        now = time.time()
        with self._lock:
            expiry = self._blocked_ips.get(ip)
        if expiry and now > expiry:
            with self._lock:
                self._blocked_ips.pop(ip, None)
            return False
        return bool(expiry)

    def _check_rate_limit(self, source_ip: str, endpoint: str):
        now = time.time()
        key = f"{source_ip}:{endpoint}"
        with self._lock:
            timestamps = self._rate_limit_violations.get(key, [])
            timestamps = [t for t in timestamps if now - t < self._rapid_window]
            self._rate_limit_violations[key] = timestamps
            if len(timestamps) >= self._rapid_threshold:
                self.block_ip(source_ip, ttl=1800)


api_attack_detector = APIAttackDetector()
