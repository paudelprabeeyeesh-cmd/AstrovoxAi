"""Comprehensive input validation and injection defense.

Provides:
1. SQL injection pattern detection (SQLi)
2. NoSQL injection pattern detection
3. Command injection detection
4. Path traversal detection
5. XSS pattern detection
6. SSRF detection in inputs
7. Length/size enforcement
8. Type validation helpers
"""

from __future__ import annotations

import ipaddress
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

SQLI_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\b(union\s+all\s+select|union\s+select)\b"), "union_select"),
    (re.compile(r"(?i)\b(select\s+.*?\s+from|insert\s+into|update\s+\w+\s+set|delete\s+from)\b"), "dml"),
    (re.compile(r"(?i)\bdrop\s+(table|database|index|trigger)\b"), "drop"),
    (re.compile(r"(?i)\balter\s+(table|database)\b"), "alter"),
    (re.compile(r"(?i)\b(or|and)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?\b"), "boolean_tautology"),
    (re.compile(r"(?i)\b(or|and)\s+['\"]?[a-z]+['\"]?\s*=\s*['\"]?[a-z]+['\"]?\b"), "boolean_tautology_str"),
    (re.compile(r"(?i)\bexec(\s|\()+\w+\b"), "exec"),
    (re.compile(r"(?i)\bwaitfor\s+delay\b"), "waitfor"),
    (re.compile(r"(?i)\bpg_sleep\b"), "pg_sleep"),
    (re.compile(r"(?i)\bchar\s*\(\s*\d+\s*\)\b"), "char_injection"),
    (re.compile(r"(?i)\bconcat\s*\([^)]*\)\b"), "concat_injection"),
    (re.compile(r"(?i)\bversion\s*\(\s*\)\b"), "version"),
    (re.compile(r"(?i)\binformation_schema\b"), "information_schema"),
    (re.compile(r"(?i)\bsqlite_master\b"), "sqlite_master"),
    (re.compile(r"(?i)\bsysobjects\b"), "sysobjects"),
    (re.compile(r"(?i)\bv\$\w+\b"), "oracle_view"),
    (re.compile(r"(?i)\b(all|any)\s+select\b"), "all_any_select"),
]

NOSQLI_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\$where\b"), "mongo_where"),
    (re.compile(r"(?i)\$ne\s*:\s*(true|1|\"1\"|'1')\b"), "mongo_ne_true"),
    (re.compile(r"(?i)\$gt\s*:\s*['\"]?\d+['\"]?\b"), "mongo_gt"),
    (re.compile(r"(?i)\$regex\s*:\s*"), "mongo_regex"),
    (re.compile(r"(?i)\$or\s*:\s*\["), "mongo_or"),
    (re.compile(r"(?i)\$and\s*:\s*\["), "mongo_and"),
    (re.compile(r"(?i)this\s*\.\s*\w+\s*==\s*"), "mongo_js_injection"),
    (re.compile(r"(?i)function\s*\(.*?\)\s*\{.*return\s+true"), "mongo_js_true"),
]

CMD_INJECTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)(;|\|\||\||&&|`|\$\(|\$\()\s*(cat|ls|dir|whoami|id|uname|pwd|nc|curl|wget|python|perl|ruby|php|bash|sh|cmd|powershell)"), "cmd_chain"),
    (re.compile(r"(?i)\b(rm\s+-rf|mv\s+|cp\s+|chmod\s+|chown\s+)\b"), "file_cmd"),
    (re.compile(r"(?i)\b(nc\s+|netcat\s+|ncat\s+)\b"), "netcat"),
    (re.compile(r"(?i)\b(echo\s+.*>|>>)\b"), "redirect"),
]

PATH_TRAVERSAL_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\.{2,}(\/|\\\\)"), "dot_dot"),
    (re.compile(r"(?i)\/etc\/(passwd|shadow|hosts)\b"), "etc_file"),
    (re.compile(r"(?i)\/proc\/(self|mem|environ)\b"), "proc_file"),
    (re.compile(r"(?i)\.\.(\/|\\\\){2,}"), "dot_dot_encoded"),
]

XSS_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)<script[^>]*>"), "script_tag"),
    (re.compile(r"(?i)javascript\s*:"), "js_scheme"),
    (re.compile(r"(?i)on\w+\s*=\s*['\"]\s*[" + "'" + r"]"), "event_handler"),
    (re.compile(r"(?i)<iframe[^>]*>"), "iframe_tag"),
    (re.compile(r"(?i)<svg[^>]*on\w+"), "svg_onload"),
    (re.compile(r"(?i)document\.(cookie|location|write|domain)"), "dom_access"),
    (re.compile(r"(?i)window\.(location|open|navigate)"), "window_access"),
    (re.compile(r"(?i)alert\s*\("), "alert"),
    (re.compile(r"(?i)expression\s*\("), "css_expression"),
    (re.compile(r"(?i)@import\s+['\"]javascript:"), "css_import"),
]

SSRF_INPUT_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\b(file|gopher|dict|php|tftp)://"), "dangerous_scheme"),
    (re.compile(r"(?i)\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "ip_address"),
    (re.compile(r"(?i)\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"), "ipv6_address"),
    (re.compile(r"(?i)localhost|127\.0\.0\.1|0\.0\.0\.0|169\.254\.169\.254"), "localhost_metadata"),
]

_PRIVATE_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "instance-data.ec2.internal",
    "169.254.169.254",
}


def _is_private_ip(host: str) -> bool:
    try:
        info = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        info.is_private
        or info.is_loopback
        or info.is_link_local
        or info.is_multicast
        or info.is_reserved
        or info.is_unspecified
    )


class InjectionFinding:
    def __init__(self, category: str, matched_pattern: str, confidence: float, details: Dict[str, Any] = None) -> None:
        self.category = category
        self.matched_pattern = matched_pattern
        self.confidence = confidence
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "matched_pattern": self.matched_pattern,
            "confidence": self.confidence,
            "details": self.details,
        }


class InputValidator:
    """Validate and detect injection attempts in user input."""

    def __init__(
        self,
        max_length: int = 100_000,
        max_value_length: int = 10_000,
        block_sqli: bool = True,
        block_nosqli: bool = True,
        block_cmd: bool = True,
        block_path_traversal: bool = True,
        block_xss: bool = True,
        block_ssrf_input: bool = True,
    ) -> None:
        self._max_length = max_length
        self._max_value_length = max_value_length
        self._block_sqli = block_sqli
        self._block_nosqli = block_nosqli
        self._block_cmd = block_cmd
        self._block_path_traversal = block_path_traversal
        self._block_xss = block_xss
        self._block_ssrf_input = block_ssrf_input

    def validate_string(self, value: str, field_name: str = "value") -> List[InjectionFinding]:
        findings: List[InjectionFinding] = []
        if not isinstance(value, str):
            return findings
        if len(value) > self._max_value_length:
            findings.append(InjectionFinding(
                category="length",
                matched_pattern="max_length_exceeded",
                confidence=1.0,
                details={"field": field_name, "length": len(value), "max": self._max_value_length},
            ))
            return findings
        if self._block_sqli:
            for pattern, tag in SQLI_PATTERNS:
                if pattern.search(value):
                    findings.append(InjectionFinding("sqli", tag, 0.9, {"field": field_name}))
        if self._block_nosqli:
            for pattern, tag in NOSQLI_PATTERNS:
                if pattern.search(value):
                    findings.append(InjectionFinding("nosqli", tag, 0.9, {"field": field_name}))
        if self._block_cmd:
            for pattern, tag in CMD_INJECTION_PATTERNS:
                if pattern.search(value):
                    findings.append(InjectionFinding("cmd_injection", tag, 0.85, {"field": field_name}))
        if self._block_path_traversal:
            for pattern, tag in PATH_TRAVERSAL_PATTERNS:
                if pattern.search(value):
                    findings.append(InjectionFinding("path_traversal", tag, 0.9, {"field": field_name}))
        if self._block_xss:
            for pattern, tag in XSS_PATTERNS:
                if pattern.search(value):
                    findings.append(InjectionFinding("xss", tag, 0.85, {"field": field_name}))
        if self._block_ssrf_input:
            for pattern, tag in SSRF_INPUT_PATTERNS:
                if pattern.search(value):
                    findings.append(InjectionFinding("ssrf_input", tag, 0.6, {"field": field_name}))
        return findings

    def validate_url(self, url: str, *, allow_private: bool = False) -> List[InjectionFinding]:
        findings = self.validate_string(url, field_name="url")
        try:
            parsed = urlparse(url)
        except Exception as exc:
            findings.append(InjectionFinding("url", "unparseable", 1.0, {"error": str(exc)}))
            return findings
        host = (parsed.hostname or "").lower()
        if not host:
            findings.append(InjectionFinding("url", "missing_host", 1.0, {}))
            return findings
        if host in _PRIVATE_HOSTNAMES:
            findings.append(InjectionFinding("ssrf", "private_hostname", 0.95, {"host": host}))
        elif not allow_private and _is_private_ip(host):
            findings.append(InjectionFinding("ssrf", "private_ip", 0.95, {"host": host}))
        if parsed.scheme not in {"http", "https"}:
            findings.append(InjectionFinding("url", "disallowed_scheme", 0.9, {"scheme": parsed.scheme}))
        return findings

    def validate_query_params(self, params: Dict[str, Any]) -> List[InjectionFinding]:
        findings: List[InjectionFinding] = []
        for key, value in params.items():
            if isinstance(value, str):
                findings.extend(self.validate_string(value, field_name=key))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        findings.extend(self.validate_string(item, field_name=key))
        return findings

    def is_safe(self, value: str) -> bool:
        return len(self.validate_string(value)) == 0

    def sanitize(self, value: str) -> str:
        if not isinstance(value, str):
            return value
        sanitized = value
        all_patterns = []
        if self._block_sqli:
            all_patterns.extend(SQLI_PATTERNS)
        if self._block_nosqli:
            all_patterns.extend(NOSQLI_PATTERNS)
        if self._block_cmd:
            all_patterns.extend(CMD_INJECTION_PATTERNS)
        if self._block_path_traversal:
            all_patterns.extend(PATH_TRAVERSAL_PATTERNS)
        if self._block_xss:
            all_patterns.extend(XSS_PATTERNS)
        for pattern, _ in all_patterns:
            sanitized = pattern.sub("[BLOCKED]", sanitized)
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", sanitized)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        if len(sanitized) > self._max_value_length:
            sanitized = sanitized[: self._max_value_length]
        return sanitized


input_validator = InputValidator()


def validate_input(value: str, field_name: str = "value") -> List[InjectionFinding]:
    return input_validator.validate_string(value, field_name)


def is_input_safe(value: str) -> bool:
    return input_validator.is_safe(value)


def sanitize_input(value: str) -> str:
    return input_validator.sanitize(value)
