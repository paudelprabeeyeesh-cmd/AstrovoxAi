from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.plugins.schema import PluginManifest


@dataclass
class ScanResult:
    passed: bool
    findings: List[Dict[str, Any]] = field(default_factory=list)
    risk_score: int = 0

    def add_finding(self, *, severity: str, rule: str, detail: str) -> None:
        self.findings.append({"severity": severity, "rule": rule, "detail": detail})
        score = {"low": 1, "medium": 3, "high": 7, "critical": 10}.get(severity, 0)
        self.risk_score += score
        self.passed = self.risk_score == 0


class PluginSecurityScanner:
    FORBIDDEN_IMPORTS = {
        "os.system",
        "subprocess.call",
        "subprocess.run",
        "shutil.rmtree",
        "eval(",
        "exec(",
        "__import__",
    }
    MAX_RISK_SCORE = 10

    def __init__(self, *, allowed_signatures: Optional[Dict[str, str]] = None) -> None:
        self.allowed_signatures = allowed_signatures or {}

    def scan_manifest(self, manifest: PluginManifest) -> ScanResult:
        result = ScanResult(passed=True)
        if not manifest.id or not manifest.version:
            result.add_finding(
                severity="high", rule="manifest-incomplete", detail="Missing id or version"
            )
        if manifest.entrypoint.endswith(".py"):
            result.add_finding(
                severity="medium",
                rule="entrypoint-validation",
                detail="Python entrypoints require sandbox validation",
            )
        return result

    def scan_code(self, code: str, *, plugin_id: str) -> ScanResult:
        result = ScanResult(passed=True)
        lowered = code.lower()
        for token in self.FORBIDDEN_IMPORTS:
            if token in lowered:
                result.add_finding(
                    severity="critical",
                    rule="forbidden-api",
                    detail=f"Forbidden token detected: {token}",
                )
        return result

    def verify_signature(self, *, plugin_id: str, payload: bytes, signature: str) -> bool:
        secret = self.allowed_signatures.get(plugin_id)
        if not secret:
            return False
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
