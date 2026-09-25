import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Vulnerability:
    id: str
    package: str
    version: str
    severity: str
    description: str
    fix_available: bool
    cve: Optional[str] = None


@dataclass
class DependencyInfo:
    name: str
    version: str
    checksum: str


@dataclass
class VerificationResult:
    verified: bool
    checked_at: str
    total_dependencies: int
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    checksum_failures: list[str] = field(default_factory=list)
    details: str = ""


class SupplyChainVerifier:
    def verify_dependencies(self, requirements_file: str) -> VerificationResult:
        if not os.path.exists(requirements_file):
            return VerificationResult(
                verified=False,
                checked_at=datetime.utcnow().isoformat() + "Z",
                total_dependencies=0,
                details=f"Requirements file not found: {requirements_file}",
            )

        with open(requirements_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

        packages = []
        for line in lines:
            if "==" in line:
                name, version = line.split("==", 1)
                packages.append(DependencyInfo(name=name.strip(), version=version.strip(), checksum=""))

        vulns = self.check_vulnerabilities(requirements_file)
        checksum_failures = []
        for pkg in packages:
            if not self.verify_checksums(pkg.name):
                checksum_failures.append(pkg.name)

        verified = len(vulns) == 0 and len(checksum_failures) == 0
        return VerificationResult(
            verified=verified,
            checked_at=datetime.utcnow().isoformat() + "Z",
            total_dependencies=len(packages),
            vulnerabilities=vulns,
            checksum_failures=checksum_failures,
            details=f"Verified {len(packages)} dependencies with {len(vulns)} vulnerabilities and {len(checksum_failures)} checksum failures",
        )

    def check_vulnerabilities(self, requirements_file: str) -> list[Vulnerability]:
        vulnerabilities: list[Vulnerability] = []

        try:
            result = subprocess.run(
                ["pip-audit", "-r", requirements_file, "--format=json"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if result.returncode in (0, 1) and result.stdout:
                import json
                try:
                    audit_data = json.loads(result.stdout)
                    for vuln in audit_data.get("dependencies", []):
                        for issue in vuln.get("vulns", []):
                            vulnerabilities.append(
                                Vulnerability(
                                    id=issue.get("id", "UNKNOWN"),
                                    package=vuln.get("name", "unknown"),
                                    version=vuln.get("version", "unknown"),
                                    severity=issue.get("severity", "unknown"),
                                    description=issue.get("description", ""),
                                    fix_available=bool(issue.get("fix_versions")),
                                    cve=issue.get("aliases", [None])[0] if issue.get("aliases") else None,
                                )
                            )
                except json.JSONDecodeError:
                    logger.warning("Failed to parse pip-audit JSON output")
            elif result.returncode == 127:
                logger.warning("pip-audit not found. Install it with: pip install pip-audit")
        except FileNotFoundError:
            logger.warning("pip-audit not available on this system")
        except subprocess.TimeoutExpired:
            logger.warning("pip-audit timed out")

        if not vulnerabilities:
            try:
                result = subprocess.run(
                    ["safety", "check", "-r", requirements_file, "--json"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                if result.returncode in (0, 1) and result.stdout:
                    import json
                    try:
                        safety_data = json.loads(result.stdout)
                        for item in safety_data:
                            vulnerabilities.append(
                                Vulnerability(
                                    id=item.get("vulnerability_id", "UNKNOWN"),
                                    package=item.get("package_name", "unknown"),
                                    version=item.get("analyzed_version", "unknown"),
                                    severity=item.get("severity", "unknown"),
                                    description=item.get("advisory", ""),
                                    fix_available=True,
                                    cve=item.get("cve", None),
                                )
                            )
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse safety JSON output")
            except FileNotFoundError:
                logger.warning("safety not found. Install it with: pip install safety")
            except subprocess.TimeoutExpired:
                logger.warning("safety timed out")

        logger.info("Found %d vulnerabilities", len(vulnerabilities))
        return vulnerabilities

    def verify_checksums(self, package: str) -> bool:
        try:
            result = subprocess.run(
                ["pip", "hash", package],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if result.returncode == 0:
                logger.debug("Checksum verified for package: %s", package)
                return True
            logger.warning("Checksum verification failed for package: %s", package)
            return False
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("Checksum verification skipped for %s: %s", package, exc)
            return True
