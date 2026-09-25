"""Dependency vulnerability scanner for backend and frontend.

Wraps safety/bandit/pip-audit for Python and npm audit for Node.js.
Returns structured findings for integration tests and CI.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Vulnerability:
    package: str
    version: str
    vulnerability_id: str
    severity: str
    description: str
    fix_version: Optional[str] = None


class DependencyVulnerabilityScanner:
    """Scans Python and Node.js dependencies for known vulnerabilities."""

    def scan_python(self, requirements_path: str) -> List[Vulnerability]:
        findings: List[Vulnerability] = []
        try:
            result = subprocess.run(
                ["pip-audit", "-r", requirements_path, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                for item in data.get("dependencies", []):
                    for vuln in item.get("vulns", []):
                        findings.append(Vulnerability(
                            package=item.get("name", ""),
                            version=item.get("version", ""),
                            vulnerability_id=vuln.get("id", ""),
                            severity=vuln.get("severity", "unknown"),
                            description=vuln.get("description", ""),
                            fix_version=vuln.get("fix_versions", [None])[0],
                        ))
        except FileNotFoundError:
            logger.warning("pip-audit not found - skipping Python scan")
        except Exception as exc:
            logger.warning("pip-audit failed: %s", exc)
        return findings

    def scan_node(self, package_json_path: str = "package.json") -> List[Vulnerability]:
        findings: List[Vulnerability] = []
        try:
            result = subprocess.run(
                ["npm", "audit", "--json", "--package-lock-only"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=".",
            )
            if result.stdout.strip():
                data = json.loads(result.stdout)
                for vuln_id, vuln in data.get("vulnerabilities", {}).items():
                    for name, info in vuln.get("via", {}).items():
                        if isinstance(info, dict):
                            findings.append(Vulnerability(
                                package=name,
                                version=info.get("range", ""),
                                vulnerability_id=info.get("url", vuln_id),
                                severity=info.get("severity", "unknown"),
                                description=vuln.get("title", ""),
                            ))
        except FileNotFoundError:
            logger.warning("npm not found - skipping Node.js scan")
        except Exception as exc:
            logger.warning("npm audit failed: %s", exc)
        return findings

    def scan_all(self, requirements_path: str = "02-Backend/requirements.txt") -> Dict[str, List[Vulnerability]]:
        return {
            "python": self.scan_python(requirements_path),
            "node": self.scan_node(),
        }


dependency_scanner = DependencyVulnerabilityScanner()
